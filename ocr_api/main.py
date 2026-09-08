"""FastAPI OCR microservice."""

from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import logging
import os
import re
import tempfile
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from html import escape as html_escape
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING

import cv2
import httpx
import numpy as np
import pytesseract
import uvicorn
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from PIL import Image, ImageOps

from ocr_api.config import settings
from ocr_api.models import HealthResponse, JobResponse, JobStatus, OCRResponse

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("uvicorn.error")


def _safe_unlink(path: Path) -> None:
    """Safely remove a file ignoring filesystem errors."""
    with contextlib.suppress(OSError):
        os.unlink(path)


# ---------------------------------------------------------------------------
# In-Memory JobStore
# ---------------------------------------------------------------------------


@dataclass
class JobRecord:
    """In-memory record for a processing job."""

    job_id: str
    status: JobStatus
    created_at: datetime
    resultado: OCRResponse | None = None
    error: str | None = None
    image_path: Path | None = None


class JobStore:
    """Thread-safe in-memory store for OCR job records."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._family_jobs: dict[int, str] = {}
        self._lock = Lock()

    def create(self, job_id: str | None = None) -> JobRecord:
        """Create a new job record with PENDING status."""
        jid = job_id or str(uuid.uuid4())
        record = JobRecord(
            job_id=jid,
            status=JobStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        with self._lock:
            self._jobs[jid] = record
        return record

    def set_family_job(self, familia_id: int, job_id: str) -> None:
        """Associate the latest job with a family ID for tab reload recovery."""
        with self._lock:
            self._family_jobs[familia_id] = job_id

    def get_family_job(self, familia_id: int) -> JobRecord | None:
        """Retrieve and consume the latest completed job for a family."""
        with self._lock:
            jid = self._family_jobs.get(familia_id)
            if not jid:
                return None
            record = self._jobs.get(jid)
            if record and record.status == JobStatus.COMPLETED:
                del self._family_jobs[familia_id]
                return record
            return None

    def get(self, job_id: str) -> JobRecord | None:
        """Retrieve a job record by ID."""
        with self._lock:
            return self._jobs.get(job_id)

    def update(
        self,
        job_id: str,
        status: JobStatus,
        resultado: OCRResponse | None = None,
        error: str | None = None,
    ) -> JobRecord:
        """Update job status and optionally set result or error message."""
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                record = JobRecord(
                    job_id=job_id,
                    status=status,
                    created_at=datetime.now(UTC),
                    resultado=resultado,
                    error=error,
                )
                self._jobs[job_id] = record
                return record

            record.status = status
            if resultado is not None:
                record.resultado = resultado
            if error is not None:
                record.error = error
            return record

    def cleanup(self, ttl_seconds: int) -> int:
        """Purge records older than ttl_seconds. Returns number of purged jobs."""
        now = datetime.now(UTC)
        with self._lock:
            expired_keys = [
                jid
                for jid, rec in self._jobs.items()
                if (now - rec.created_at).total_seconds() > ttl_seconds
            ]
            for jid in expired_keys:
                rec = self._jobs.pop(jid, None)
                if rec and rec.image_path:
                    _safe_unlink(rec.image_path)
            return len(expired_keys)

    def active_jobs_count(self) -> int:
        """Count jobs currently pending or processing."""
        with self._lock:
            return sum(
                1
                for rec in self._jobs.values()
                if rec.status in (JobStatus.PENDING, JobStatus.PROCESSING)
            )


job_store = JobStore()


# ---------------------------------------------------------------------------
# Currency and LLM Parser Helpers
# ---------------------------------------------------------------------------


def _resolve_currency(val: object) -> str:
    """Normalize currency code detected by OCR.

    Only UYU and USD are valid. Any other value or None defaults to UYU.
    """
    if not val or str(val).strip().lower() in ("null", "none", "n/a", "-"):
        return "UYU"
    ccy = str(val).strip().upper()
    return ccy if ccy in {"UYU", "USD"} else "UYU"


def _str_or_none(val: object) -> str | None:
    """Convert empty or null-like strings to None."""
    if not val or str(val).strip().lower() in ("null", "none", "n/a", "-"):
        return None
    return str(val)


def _parse_decimal_str(raw_num: str) -> Decimal | None:
    """Convert raw receipt number string to Decimal safely without float inaccuracy."""
    raw = raw_num.strip().replace(" ", "")
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        parts = raw.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            raw = parts[0] + "." + parts[1]
        else:
            raw = raw.replace(",", "")
    try:
        val = Decimal(raw)
        if Decimal("0.00") < val < Decimal("10000000.00"):
            return val
    except (InvalidOperation, ValueError):
        pass
    return None


_PROMPT_PARSEO = (
    "Analizá el texto de este ticket de compra uruguayo y extraé los datos.\n"
    "Respondé ÚNICAMENTE con un JSON válido, sin texto adicional ni explicaciones, "
    "con esta estructura exacta:\n"
    "{{\n"
    '  "monto": null,\n'
    '  "fecha": null,\n'
    '  "comercio": null,\n'
    '  "items": [],\n'
    '  "currency": null\n'
    "}}\n"
    "\n"
    "Reglas estrictas:\n"
    "- 'monto': El total pagado que figure en el texto (ej: 790.0 o null). "
    "NO inventes montos.\n"
    "- 'fecha': Fecha en formato YYYY-MM-DD o null.\n"
    "- 'comercio': Nombre del local o empresa que emite el ticket o null.\n"
    "- 'items': Lista de productos o artículos comprados que figuren en el texto.\n"
    "- 'currency': 'UYU' (si es pesos o $) o 'USD' (si es dólares) o null.\n"
    "- IMPORTANTE: Extraé EXCLUSIVAMENTE datos que aparezcan en el ticket. "
    "NO inventes nada.\n"
    "\n"
    "Texto del ticket:\n"
    "{texto}"
)


# ---------------------------------------------------------------------------
# Background Cleanup and Application Lifespan
# ---------------------------------------------------------------------------


async def _periodic_cleanup(ttl_seconds: int) -> None:
    """Periodically purge expired jobs from JobStore."""
    while True:
        try:
            await asyncio.sleep(60)
            purged = job_store.cleanup(ttl_seconds)
            if purged > 0:
                logger.info("[JobStore] Evicted %d expired jobs", purged)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning("[JobStore] Cleanup error: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle."""
    logger.info("🚀 OCR Service started on port %d", settings.api_port)
    cleanup_task = asyncio.create_task(_periodic_cleanup(settings.job_ttl_seconds))
    try:
        yield
    finally:
        cleanup_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await cleanup_task
        logger.info("👋 OCR Service stopped")


app = FastAPI(
    title="OCR API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Image Preprocessing & OCR Extraction
# ---------------------------------------------------------------------------


def preprocesar_imagen(imagen: Image.Image, profile: str = "thermal") -> Image.Image:
    """Preprocess receipt image optimized for ARM / Orange Pi 5 Plus.

    - Convert to grayscale.
    - If profile is 'thermal': CLAHE contrast equalization and adaptive
      Gaussian thresholding to rescue low-contrast thermal receipts.
    - Otherwise: contrast normalization + Otsu binarization.
    """
    img = np.array(imagen)
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    h, w = img.shape[:2]
    max_dim = max(h, w)
    if max_dim > 1280:
        scale = 1280.0 / max_dim
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    if profile == "thermal":
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(img)
        blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 11
        )
        return Image.fromarray(thresh)

    img = cv2.normalize(img, img, 0, 255, cv2.NORM_MINMAX)
    blurred = cv2.GaussianBlur(img, (3, 3), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return Image.fromarray(thresh)


PALABRAS_CLAVE_TICKET = {
    "TOTAL",
    "RUT",
    "FECHA",
    "PESOS",
    "UYU",
    "SUBTOTAL",
    "PAGAR",
    "CONSUMO",
    "FACTURA",
    "TICKET",
    "CONTADO",
    "IVA",
    "EFECTIVO",
    "CAMBIO",
    "TASA",
    "BASICA",
    "DESCUENTO",
    "IMPORTE",
}


def _evaluar_calidad_ocr(texto: str) -> tuple[Decimal | None, int]:
    """Evalúa calidad del texto extraído retornando (monto, cant_palabras_clave)."""
    if not texto or len(texto.strip()) < 5:
        return None, 0
    datos = extraer_datos_regex(texto)
    monto = datos.get("monto")
    upper = texto.upper()
    keywords = sum(1 for kw in PALABRAS_CLAVE_TICKET if re.search(rf"\b{kw}\b", upper))
    return monto, keywords


def _ejecutar_tesseract_imagen(imagen: Image.Image, timeout: int = 15) -> str:
    """Ejecuta pytesseract.image_to_string con manejo de excepciones."""
    try:
        return pytesseract.image_to_string(
            imagen,
            lang="spa",
            config="--psm 3 --oem 3",
            timeout=timeout,
        )
    except Exception:
        try:
            return pytesseract.image_to_string(imagen, lang="spa", timeout=10)
        except Exception:
            return ""


def _run_tesseract(imagen_path: Path) -> tuple[str, float]:
    """Synchronously run preprocessing, auto-orientation, and fast Tesseract OCR."""
    with Image.open(imagen_path) as img:
        img = ImageOps.exif_transpose(img)
        # Default to thermal CLAHE profile
        imagen_base = preprocesar_imagen(img, profile="thermal")

    # 1. Orientación normal (0°)
    texto_0 = _ejecutar_tesseract_imagen(imagen_base, timeout=12)
    monto_0, kw_0 = _evaluar_calidad_ocr(texto_0)

    # Si a 0° con perfil térmico no encontró monto ni keywords, probar con Otsu
    if monto_0 is None and kw_0 < 1:
        with Image.open(imagen_path) as img:
            img = ImageOps.exif_transpose(img)
            imagen_otsu = preprocesar_imagen(img, profile="standard")
        texto_otsu = _ejecutar_tesseract_imagen(imagen_otsu, timeout=10)
        monto_otsu, kw_otsu = _evaluar_calidad_ocr(texto_otsu)
        if monto_otsu is not None or kw_otsu > kw_0:
            imagen_base = imagen_otsu
            texto_0 = texto_otsu
            monto_0 = monto_otsu
            kw_0 = kw_otsu

    # Si a 0° ya encontró monto y al menos una keyword, la orientación es correcta
    if monto_0 is not None and kw_0 >= 1:
        clean_text = "\n".join(line for line in texto_0.splitlines() if line.strip())
        return clean_text, 0.88

    # 2. Si no encontró monto o faltan keywords, probar rotación 180° (ticket invertido)
    img_180 = imagen_base.rotate(180, expand=True)
    texto_180 = _ejecutar_tesseract_imagen(img_180, timeout=12)
    monto_180, kw_180 = _evaluar_calidad_ocr(texto_180)

    if monto_180 is not None or kw_180 > kw_0:
        clean_text = "\n".join(line for line in texto_180.splitlines() if line.strip())
        confianza = 0.88 if monto_180 is not None else 0.50
        logger.info(
            "[OCR] Auto-orientación 180° seleccionada (kw_0=%d -> kw_180=%d, monto=%s)",
            kw_0,
            kw_180,
            monto_180,
        )
        return clean_text, confianza

    # 3. Si la imagen es apaisada (width > height) y no hay monto, probar 90° y 270°
    if imagen_base.width > imagen_base.height and monto_0 is None:
        for angulo in (90, 270):
            img_rot = imagen_base.rotate(angulo, expand=True)
            txt_rot = _ejecutar_tesseract_imagen(img_rot, timeout=10)
            m_rot, kw_rot = _evaluar_calidad_ocr(txt_rot)
            if m_rot is not None or kw_rot > kw_0 + 1:
                clean_text = "\n".join(
                    line for line in txt_rot.splitlines() if line.strip()
                )
                confianza = 0.88 if m_rot is not None else 0.50
                logger.info(
                    "[OCR] Auto-orientación %d° seleccionada (kw=%d, monto=%s)",
                    angulo,
                    kw_rot,
                    m_rot,
                )
                return clean_text, confianza

    mejor_texto = texto_180 if kw_180 > kw_0 else texto_0
    clean_text = "\n".join(line for line in mejor_texto.splitlines() if line.strip())
    confianza = 0.88 if (monto_0 is not None or monto_180 is not None) else 0.35
    return clean_text, confianza


async def extraer_texto_tesseract(imagen_path: Path) -> tuple[str, float]:
    """Extract text from image offloaded to a worker thread."""
    try:
        texto_crudo, confianza = await asyncio.to_thread(_run_tesseract, imagen_path)
        logger.info(
            "[OCR] Extracted %d chars (confidence=%.2f)",
            len(texto_crudo),
            confianza,
        )
        return texto_crudo, confianza
    except Exception as e:
        logger.error("[OCR] Tesseract error: %s", e)
        return "", 0.0


def _detect_image_mime_type(image_bytes: bytes) -> str:
    """Detect image MIME type from magic numbers or fallback to JPEG."""
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if (
        image_bytes.startswith(b"RIFF")
        and len(image_bytes) >= 12
        and image_bytes[8:12] == b"WEBP"
    ):
        return "image/webp"
    return "image/jpeg"


def extraer_datos_regex(texto: str) -> dict:
    """Fallback heuristic and regex extractor for Uruguayan receipts.

    Parses total amount, subtotal, tax, rut, document type, date, store name,
    and currency directly from raw OCR text with strict Decimal arithmetic.
    """
    if not texto:
        return {}

    lines = [line.strip() for line in texto.split("\n") if line.strip()]
    full_text = " ".join(lines)

    # 1. Currency
    currency = "UYU"
    if re.search(r"\b(USD|U\$S|US\$|DOLARES|DOLAR)\b", full_text, re.IGNORECASE):
        currency = "USD"

    # 2. Date
    fecha: str | None = None
    date_match = re.search(r"\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})\b", full_text)
    if date_match:
        d_str, m_str, y_str = date_match.groups()
        try:
            day = int(d_str)
            month = int(m_str)
            year = int(y_str)
            if year < 100:
                year += 2000
            if 1 <= day <= 31 and 1 <= month <= 12 and 2000 <= year <= 2035:
                fecha = f"{year:04d}-{month:02d}-{day:02d}"
        except (ValueError, TypeError):
            fecha = None

    if not fecha:
        iso_match = re.search(r"\b(20\d{2})[/\-](\d{2})[/\-](\d{2})\b", full_text)
        if iso_match:
            y, m, d = iso_match.groups()
            fecha = f"{y}-{m}-{d}"

    # 3. Numeric patterns
    num_pat = (
        r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{1,2})|[0-9]+(?:[.,][0-9]{1,2})?)"
    )
    ccy_prefix = r"[:;\.\$]?\s*(?:UYU|USD|\$|U\$S)?\s*[:;\.\-_~*oO0]*\s*"

    # 3a. Total Amount
    monto: Decimal | None = None
    explicit_total_patterns = [
        rf"(?:TOTAL A PAGAR|TOTAL PAGADO|TOTAL FINAL)\s*{ccy_prefix}{num_pat}",
        rf"(?:IMPORTE TOTAL|A PAGAR|PAGO CONTADO)\s*{ccy_prefix}{num_pat}",
    ]
    generic_total_patterns = [
        rf"(?<!SUB)(?<!DES)\bTOTAL\b\s*{ccy_prefix}{num_pat}",
    ]
    secondary_patterns = [
        rf"(?:SUBTOTAL|IMPORTE|TOT)\s*{ccy_prefix}{num_pat}",
        rf"(?:UYU|USD|\$|U\$S)\s*{num_pat}",
    ]

    def _extract_from_patterns(patterns: list[str]) -> list[Decimal]:
        results: list[Decimal] = []
        for pattern in patterns:
            for m in re.finditer(pattern, full_text, re.IGNORECASE):
                start_idx = m.start()
                preceding = full_text[max(0, start_idx - 15) : start_idx].upper()
                if "CANTIDAD" in preceding or "CANT" in preceding:
                    continue
                val = _parse_decimal_str(m.group(1))
                if val is not None:
                    results.append(val)
        return results

    explicit_candidates = _extract_from_patterns(explicit_total_patterns)
    if explicit_candidates:
        monto = explicit_candidates[-1]
    else:
        generic_candidates = _extract_from_patterns(generic_total_patterns)
        if generic_candidates:
            monto = generic_candidates[-1]
        else:
            secondary_candidates = _extract_from_patterns(secondary_patterns)
            if secondary_candidates:
                monto = secondary_candidates[-1]

    # Fallback por línea para total si el regex directo falló por ruido
    if monto is None:
        for line in lines:
            upper_l = line.upper()
            if "TOTAL" in upper_l and "SUB" not in upper_l and "CANT" not in upper_l:
                line_nums = list(re.finditer(num_pat, line))
                if line_nums:
                    val = _parse_decimal_str(line_nums[-1].group(1))
                    if val is not None and val > Decimal("0.00"):
                        monto = val
                        break

    # 3b. Subtotal
    subtotal: Decimal | None = None
    sub_m = re.search(
        rf"(?:SUB\s*TOTAL|SUBTOTAL)\s*(?:TASA BASICA|BASICA)?\s*{ccy_prefix}{num_pat}",
        full_text,
        re.IGNORECASE,
    )
    if sub_m:
        subtotal = _parse_decimal_str(sub_m.group(1))
    if subtotal is None:
        for line in lines:
            upper_l = line.upper()
            if (
                "SUBTOTAL" in upper_l or "SUB TOTAL" in upper_l
            ) and "IVA" not in upper_l:
                line_nums = list(re.finditer(num_pat, line))
                if line_nums:
                    val = _parse_decimal_str(line_nums[-1].group(1))
                    if val is not None:
                        subtotal = val
                        break

    # 3c. Tax (IVA)
    tax: Decimal | None = None
    tax_m = re.search(
        rf"(?:IVA|IMPUESTO)\s*(?:TASA BASICA|BASICA)?\s*{ccy_prefix}{num_pat}",
        full_text,
        re.IGNORECASE,
    )
    if tax_m:
        tax = _parse_decimal_str(tax_m.group(1))
    if tax is None:
        for line in lines:
            upper_l = line.upper()
            if ("IVA" in upper_l or "IMPUESTO" in upper_l) and "TOTAL" not in upper_l:
                line_nums = list(re.finditer(num_pat, line))
                if line_nums:
                    val = _parse_decimal_str(line_nums[-1].group(1))
                    if val is not None:
                        tax = val
                        break

    # 3d. Line amount & Payment amount
    pay_m = re.search(
        rf"(?:EFECTIVO|TARJETA|DEBITO|CREDITO)\s*{ccy_prefix}{num_pat}",
        full_text,
        re.IGNORECASE,
    )
    payment_amount: Decimal | None = (
        _parse_decimal_str(pay_m.group(1)) if pay_m else None
    )

    line_m = re.search(rf"\bUN\b.*?{num_pat}\s+{num_pat}", full_text)
    line_amount: Decimal | None = (
        _parse_decimal_str(line_m.group(2)) if line_m else None
    )

    # 4. RUT & Document Type
    rut_m = re.search(
        r"\b(?:RUT(?:\s*EMISOR)?[:\s]*)?([0-9]{12})\b", full_text, re.IGNORECASE
    )
    rut: str | None = rut_m.group(1) if rut_m else None

    doc_m = re.search(
        r"\b(e-TICKET|e-FACTURA|FACTURA|TICKET|BOLETA)\b", full_text, re.IGNORECASE
    )
    document_type: str | None = doc_m.group(1).upper() if doc_m else None

    # 5. Arithmetic Consistency (never altering visual extracted numbers)
    arithmetic_consistent: bool | None = None
    if subtotal is not None and tax is not None and monto is not None:
        arithmetic_consistent = subtotal + tax == monto

    # 6. Store name
    comercio: str | None = None
    known_stores = [
        "TIENDA INGLESA",
        "DEVOTO",
        "DISCO",
        "TATA",
        "TA-TA",
        "GEANT",
        "FARMASHOP",
        "SAN ROQUE",
        "MACROMERCADO",
        "MACRO MERCADO",
        "SODIMAC",
        "ANCAP",
        "DISA",
        "AXION",
        "PETROBRAS",
        "EL CLON",
        "OPLAROS",
        "FARMACIA",
        "SUPERMERCADO",
        "PANADERIA",
        "CARNICERIA",
        "VERDULERIA",
        "FERRETERIA",
        "AGROPECUARIA",
        "VETERINARIA",
    ]
    upper_full = full_text.upper()
    for store in known_stores:
        if store in upper_full:
            comercio = store.title()
            break

    keywords_count = sum(
        1 for kw in PALABRAS_CLAVE_TICKET if re.search(rf"\b{kw}\b", upper_full)
    )

    if not comercio and lines and (monto is not None or keywords_count >= 2):
        for line in lines[:4]:
            clean = re.sub(r"[^A-Za-zÁÉÍÓÚáéíóúÑñ\s]", "", line).strip()
            upper_clean = clean.upper()
            if 3 <= len(clean) <= 35 and not any(
                w in upper_clean
                for w in (
                    "RUT",
                    "FECHA",
                    "HORA",
                    "TICKET",
                    "FACTURA",
                    "CAJA",
                    "LOCAL",
                    "CONSUMO",
                    "CLIENTE",
                    "DATOS",
                    "TOTAL",
                )
            ):
                palabras = clean.split()
                if any(len(p) >= 3 for p in palabras):
                    comercio = clean.title()
                    break

    # 7. Items extraction from text lines
    extracted_items: list[str] = []
    stop_words = {
        "RUT",
        "FECHA",
        "HORA",
        "TOTAL",
        "SUBTOTAL",
        "TICKET",
        "FACTURA",
        "CAJA",
        "LOCAL",
        "CAJERO",
        "MONTO",
        "CAMBIO",
        "EFECTIVO",
        "TARJETA",
        "IVA",
        "REDONDEO",
        "GRACIAS",
        "VISITA",
        "DISCO",
        "DEVOTO",
        "TATA",
        "GEANT",
        "PAGO",
        "IMPORTA",
        "SERIE",
        "SUCURSAL",
        "CONSUMO",
        "CLIENTE",
        "DIRECCION",
        "TEL",
        "R.U.T",
        "I.V.A",
        "D.G.I",
        "CONTADO",
        "CREDITO",
        "TIENDA INGLESA",
    }
    if monto is not None or keywords_count >= 2:
        for line in lines:
            upper_l = line.upper()
            if any(sw in upper_l for sw in stop_words):
                continue
            clean_item = re.sub(r"[\$0-9\.,]{2,}", "", line)
            clean_item = re.sub(r"[^A-Za-zÁÉÍÓÚáéíóúÑñ\s]", "", clean_item).strip()
            if 4 <= len(clean_item) <= 40:
                item_title = clean_item.title()
                if item_title not in extracted_items:
                    extracted_items.append(item_title)

    # 8. Extraction confidence (Visual legibility and completeness)
    conf = 0.0
    if monto is not None:
        conf += 0.35
    if comercio or rut:
        conf += 0.25
    if fecha:
        conf += 0.20
    if subtotal is not None or tax is not None or line_amount is not None:
        conf += 0.15
    if currency:
        conf += 0.05
    if monto is None:
        conf = min(conf, 0.35)
    extraction_confidence = min(round(conf, 2), 1.0)

    return {
        "monto": monto,
        "subtotal": subtotal,
        "tax": tax,
        "line_amount": line_amount,
        "payment_amount": payment_amount,
        "rut": rut,
        "document_type": document_type,
        "fecha": fecha,
        "comercio": comercio,
        "currency": currency,
        "items": extracted_items[:5],
        "arithmetic_consistent": arithmetic_consistent,
        "extraction_confidence": extraction_confidence,
    }


def _es_monto_valido_en_texto(monto: Decimal | None, texto: str) -> bool:
    """Verifica si el monto extraído por el LLM realmente figura en el texto OCR."""
    if monto is None or not texto:
        return False
    int_str = str(int(round(float(monto))))
    if int_str in texto:
        return True
    str_val = f"{monto:.2f}"
    if str_val in texto or str_val.replace(".", ",") in texto:
        return True
    return False


def _filtrar_items_reales(items: list, texto: str) -> list[str]:
    """Descarta items alucinados por el LLM que no figuren en el ticket."""
    if not items or not texto:
        return []
    texto_lower = texto.lower()
    items_validos = []
    for item in items:
        if isinstance(item, dict):
            item = item.get("nombre") or item.get("name") or item.get("item") or ""
        if not isinstance(item, str) or not item.strip():
            continue
        item_clean = item.strip()
        palabras = [w for w in re.split(r"\s+", item_clean.lower()) if len(w) >= 2]
        if palabras and all(
            re.search(rf"\b{re.escape(p)}\b", texto_lower) for p in palabras
        ):
            items_validos.append(item_clean)
    return items_validos


async def parsear_con_ollama(texto: str) -> dict | None:
    """Parse raw OCR text using Ollama with 90s timeout."""
    if not texto.strip():
        return None

    models_to_try = [settings.ollama_model]
    for fallback_mod in ("qwen2.5:3b", "gemma2:2b", "contador-oriental:latest"):
        if fallback_mod not in models_to_try:
            models_to_try.append(fallback_mod)

    try:
        prompt = _PROMPT_PARSEO.format(texto=texto[:1500])

        async with httpx.AsyncClient(timeout=15.0) as client:
            respuesta = ""
            for current_model in models_to_try:
                try:
                    response = await client.post(
                        f"{settings.ollama_base_url}/api/generate",
                        json={
                            "model": current_model,
                            "prompt": prompt,
                            "format": "json",
                            "stream": False,
                            "options": {
                                "num_predict": 80,
                                "temperature": 0.0,
                                "num_ctx": 1024,
                                "num_thread": 4,
                            },
                        },
                    )
                    if response.status_code == 200:
                        respuesta = response.json().get("response", "")
                        if respuesta:
                            logger.info(
                                "[PARSER] Succeeded with Ollama model: %s",
                                current_model,
                            )
                            break
                except Exception as mod_err:
                    logger.debug(
                        "[PARSER] Model %s failed or timeout: %s",
                        current_model,
                        mod_err,
                    )

        if not respuesta:
            logger.warning("[PARSER] Ollama returned empty response")
            return None

        match = re.search(r"\{.*?\}", respuesta, re.DOTALL)
        if not match:
            logger.warning("[PARSER] No JSON object found in LLM response")
            return None

        datos = json.loads(match.group())
        logger.info(
            "[PARSER] Extracted: store=%s amount=%s",
            datos.get("comercio"),
            datos.get("monto"),
        )
        return datos

    except Exception as e:
        err_detail = f"{type(e).__name__}: {e}" if str(e) else repr(e)
        logger.warning("[PARSER] Ollama extraction failed: %s", err_detail)
        return None


_last_gemini_error: str | None = None


async def extraer_con_gemini_flash(
    image_bytes: bytes, api_key: str, model: str
) -> dict | None:
    """Extract receipt information using Gemini Flash cloud model."""
    global _last_gemini_error
    _last_gemini_error = None

    if not image_bytes or not api_key:
        _last_gemini_error = "Bytes de imagen o API key vacíos"
        return None

    models_to_try = [model]
    for fallback_mod in (
        "gemini-1.5-flash",
        "gemini-2.0-flash",
        "gemini-2.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-flash-latest",
        "gemini-2.0-flash-exp",
        "gemini-1.5-flash-8b",
    ):
        if fallback_mod not in models_to_try:
            models_to_try.append(fallback_mod)

    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    mime_type = _detect_image_mime_type(image_bytes)
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "Analizá este ticket de compra uruguayo y extraé los "
                            "datos en formato JSON.\n"
                            "Respondé con el siguiente formato exacto:\n"
                            "{\n"
                            '  "monto": null,\n'
                            '  "fecha": null,\n'
                            '  "comercio": null,\n'
                            '  "items": [],\n'
                            '  "currency": "UYU"\n'
                            "}\n"
                            "Reglas:\n"
                            "- monto: Total pagado como float (ej: 790.0) o null.\n"
                            "- fecha: Formato ISO YYYY-MM-DD o null.\n"
                            "- comercio: Nombre empresa/comercio o null.\n"
                            "- items: Lista de productos reales del ticket.\n"
                            "- currency: 'UYU' (pesos, $) o 'USD' (dólares, US$).\n"
                            "- Extraé ÚNICAMENTE datos reales presentes en la imagen."
                        )
                    },
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": b64_image,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "response_mime_type": "application/json",
        },
    }

    data = None
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for current_model in models_to_try:
                for api_version in ("v1beta", "v1"):
                    url = (
                        f"https://generativelanguage.googleapis.com/{api_version}/models/"
                        f"{current_model}:generateContent?key={api_key}"
                    )
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        logger.info(
                            "[GEMINI] Succeeded with model: %s (%s)",
                            current_model,
                            api_version,
                        )
                        break

                    body_snip = resp.text[:200]
                    _last_gemini_error = (
                        f"HTTP {resp.status_code} "
                        f"({current_model}/{api_version}): {body_snip}"
                    )
                    logger.warning(
                        "[GEMINI] Model %s (%s) failed (HTTP %d): %s",
                        current_model,
                        api_version,
                        resp.status_code,
                        resp.text[:200],
                    )
                    if resp.status_code not in (404, 400):
                        break

                if data is not None:
                    break

            # Si todos los modelos candidatos fallaron con 404/400, consultar ListModels
            if data is None:
                try:
                    logger.info(
                        "[GEMINI] Querying ListModels to discover available models..."
                    )
                    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                    list_resp = await client.get(list_url, timeout=10.0)
                    if list_resp.status_code == 200:
                        models_data = list_resp.json().get("models", [])
                        discovered = [
                            m.get("name", "").replace("models/", "")
                            for m in models_data
                            if "generateContent"
                            in m.get("supportedGenerationMethods", [])
                        ]
                        logger.info(
                            "[GEMINI] Discovered available models from Google: %s",
                            discovered,
                        )
                        flash_first = [m for m in discovered if "flash" in m.lower()]
                        other_models = [
                            m for m in discovered if "flash" not in m.lower()
                        ]
                        for disc_model in flash_first + other_models:
                            if disc_model in models_to_try:
                                continue
                            url = (
                                f"https://generativelanguage.googleapis.com/v1beta/models/"
                                f"{disc_model}:generateContent?key={api_key}"
                            )
                            resp = await client.post(url, json=payload)
                            if resp.status_code == 200:
                                data = resp.json()
                                logger.info(
                                    "[GEMINI] Succeeded with discovered model: %s",
                                    disc_model,
                                )
                                break
                            _last_gemini_error = (
                                f"HTTP {resp.status_code} "
                                f"({disc_model}): {resp.text[:200]}"
                            )
                except Exception as list_err:
                    logger.warning("[GEMINI] ListModels query failed: %s", list_err)

        if data is None:
            return None

        candidates = data.get("candidates", [])
        if not candidates:
            _last_gemini_error = "Google API respondió sin candidates"
            logger.warning("[GEMINI] No candidates in response")
            return None

        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            _last_gemini_error = "Google API respondió sin parts de contenido"
            logger.warning("[GEMINI] No content parts in response")
            return None

        raw_text = parts[0].get("text", "")
        if not raw_text:
            _last_gemini_error = "Google API respondió con texto vacío"
            logger.warning("[GEMINI] Empty text part in response")
            return None

        parsed = json.loads(raw_text)

        # Normalize amount
        monto_raw = parsed.get("monto")
        monto_val: Decimal | None = None
        if monto_raw is not None:
            monto_val = _parse_decimal_str(str(monto_raw))

        # Normalize date
        fecha_val = _str_or_none(parsed.get("fecha"))

        # Normalize store and items
        comercio_val = _str_or_none(parsed.get("comercio"))
        items_raw = parsed.get("items") or []
        items_val = [str(it) for it in items_raw] if isinstance(items_raw, list) else []

        # Normalize currency
        currency_val = _resolve_currency(parsed.get("currency"))

        # Subtotal, tax, rut
        subtotal_val = (
            _parse_decimal_str(str(parsed.get("subtotal")))
            if parsed.get("subtotal") is not None
            else None
        )
        tax_val = (
            _parse_decimal_str(str(parsed.get("tax")))
            if parsed.get("tax") is not None
            else None
        )
        rut_val = _str_or_none(parsed.get("rut"))
        doc_type_val = _str_or_none(parsed.get("document_type"))

        arithmetic_consistent: bool | None = None
        if subtotal_val is not None and tax_val is not None and monto_val is not None:
            arithmetic_consistent = subtotal_val + tax_val == monto_val

        logger.info(
            "[GEMINI] Extracted: store=%s amount=%s currency=%s",
            comercio_val,
            monto_val,
            currency_val,
        )
        return {
            "monto": monto_val,
            "subtotal": subtotal_val,
            "tax": tax_val,
            "rut": rut_val,
            "document_type": doc_type_val,
            "fecha": fecha_val,
            "comercio": comercio_val,
            "items": items_val,
            "currency": currency_val,
            "arithmetic_consistent": arithmetic_consistent,
            "extraction_confidence": 0.95,
        }
    except Exception as e:
        err_desc = f"{type(e).__name__}: {e}" if str(e) else repr(e)
        if not _last_gemini_error:
            _last_gemini_error = err_desc
        logger.error("[GEMINI] Extraction failed: %s", err_desc)
        return None


async def procesar_job_async(tmp_path: Path, engine: str = "auto") -> OCRResponse:
    """Process a single receipt image via Gemini Flash or local pipeline."""
    # 1. Cloud OCR via Gemini 2.0 Flash
    if engine in ("auto", "cloud", "gemini"):
        if settings.gemini_api_key:
            try:
                image_bytes = await asyncio.to_thread(tmp_path.read_bytes)
                gemini_data = await extraer_con_gemini_flash(
                    image_bytes=image_bytes,
                    api_key=settings.gemini_api_key,
                    model=settings.gemini_model,
                )
                if gemini_data is not None:
                    fecha_parsed: date | None = None
                    if gemini_data.get("fecha"):
                        try:
                            fecha_parsed = date.fromisoformat(str(gemini_data["fecha"]))
                        except (ValueError, TypeError):
                            pass

                    monto = gemini_data.get("monto")
                    subtotal = gemini_data.get("subtotal")
                    tax = gemini_data.get("tax")
                    rut = gemini_data.get("rut")
                    doc_type = gemini_data.get("document_type")
                    arithmetic_consistent = gemini_data.get("arithmetic_consistent")
                    comercio = gemini_data.get("comercio")
                    items = gemini_data.get("items") or []
                    currency = gemini_data.get("currency", "UYU")
                    raw_summary = (
                        f"[Gemini Flash] {comercio or ''} {monto or ''}".strip()
                    )

                    return OCRResponse(
                        success=True,
                        monto=monto,
                        subtotal=subtotal,
                        tax=tax,
                        rut=rut,
                        document_type=doc_type,
                        fecha=fecha_parsed,
                        comercio=comercio,
                        items=items,
                        currency=currency,
                        texto_crudo=raw_summary,
                        confianza_ocr=0.95,
                        extraction_confidence=0.95,
                        arithmetic_consistent=arithmetic_consistent,
                        engine_used="gemini-2.0-flash",
                    )
                if engine in ("cloud", "gemini"):
                    detail = (
                        _last_gemini_error
                        or "Respuesta vacía o formato inválido de Google API"
                    )
                    return OCRResponse(
                        success=False,
                        error=f"Gemini Flash falló: {detail}",
                        engine_used="gemini-2.0-flash",
                    )
                logger.warning(
                    "[OCR] Gemini Flash extraction was empty; "
                    "falling back to local pipeline"
                )
            except Exception as e:
                err_desc = f"{type(e).__name__}: {e}" if str(e) else repr(e)
                logger.warning(
                    "[OCR] Gemini Flash failed (%s); falling back to local pipeline",
                    err_desc,
                )
                if engine in ("cloud", "gemini"):
                    return OCRResponse(
                        success=False,
                        error=f"Error en Gemini Flash: {err_desc}",
                        engine_used="gemini-2.0-flash",
                    )
        elif engine in ("cloud", "gemini"):
            return OCRResponse(
                success=False,
                error="GEMINI_API_KEY no configurada",
                engine_used="gemini-2.0-flash",
            )

    # 2. Local pipeline (Tesseract + Ollama / Regex fallback)
    try:
        texto_crudo, confianza = await extraer_texto_tesseract(tmp_path)
        if not texto_crudo or len(texto_crudo) < 10:
            return OCRResponse(
                success=False,
                error="No se pudo extraer texto de la imagen",
                confianza_ocr=confianza,
                engine_used="local-tesseract",
            )

        regex_data = extraer_datos_regex(texto_crudo)
        subtotal = regex_data.get("subtotal")
        tax = regex_data.get("tax")
        line_amount = regex_data.get("line_amount")
        payment_amount = regex_data.get("payment_amount")
        rut = regex_data.get("rut")
        document_type = regex_data.get("document_type")
        arithmetic_consistent = regex_data.get("arithmetic_consistent")
        extraction_confidence = regex_data.get("extraction_confidence", 0.0)

        if regex_data.get("monto") is not None:
            logger.info(
                "[OCR] Regex determinístico extrajo monto=%s comercio=%s",
                regex_data.get("monto"),
                regex_data.get("comercio"),
            )
            monto = regex_data.get("monto")
            comercio = regex_data.get("comercio")
            items = regex_data.get("items") or []
            currency = _resolve_currency(regex_data.get("currency"))
            fecha_str = regex_data.get("fecha")
            engine_used = "local-tesseract-regex"
        else:
            parsed = await parsear_con_ollama(texto_crudo)
            engine_used = "local-tesseract-ollama"

            if parsed:
                # Validación anti-alucinación de monto del LLM
                monto_llm = parsed.get("monto")
                if monto_llm is not None:
                    monto_dec = _parse_decimal_str(str(monto_llm))
                    if monto_dec is not None and _es_monto_valido_en_texto(
                        monto_dec, texto_crudo
                    ):
                        monto = monto_dec
                    else:
                        monto = regex_data.get("monto")
                        engine_used = "local-tesseract-hybrid"
                else:
                    monto = regex_data.get("monto")

                # Validación anti-alucinación de items
                items_llm = parsed.get("items") or []
                valid_items = _filtrar_items_reales(items_llm, texto_crudo)
                items = valid_items if valid_items else (regex_data.get("items") or [])

                # Validación de comercio
                comercio_llm = _str_or_none(parsed.get("comercio"))
                if comercio_llm and (
                    comercio_llm.lower() in texto_crudo.lower()
                    or not regex_data.get("comercio")
                ):
                    comercio = comercio_llm
                else:
                    comercio = regex_data.get("comercio") or comercio_llm

                # Validación de currency y fecha
                currency = _resolve_currency(
                    parsed.get("currency") or regex_data.get("currency")
                )
                fecha_str = parsed.get("fecha") or regex_data.get("fecha")
            else:
                logger.info(
                    "[OCR] Ollama unavailable or empty; falling back to regex parser"
                )
                monto = regex_data.get("monto")
                items = regex_data.get("items") or []
                comercio = regex_data.get("comercio")
                currency = _resolve_currency(regex_data.get("currency"))
                fecha_str = regex_data.get("fecha")
                engine_used = "local-tesseract-regex"

        fecha_parsed_local: date | None = None
        if fecha_str:
            try:
                fecha_parsed_local = date.fromisoformat(str(fecha_str))
            except (ValueError, TypeError):
                m_date = re.match(
                    r"^(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})$",
                    str(fecha_str).strip(),
                )
                if m_date:
                    d, m, y = m_date.groups()
                    y_int = int(y) + (2000 if int(y) < 100 else 0)
                    try:
                        fecha_parsed_local = date(y_int, int(m), int(d))
                    except ValueError:
                        pass

        if monto is None and comercio is None:
            return OCRResponse(
                success=False,
                texto_crudo=texto_crudo,
                confianza_ocr=confianza,
                extraction_confidence=extraction_confidence,
                error="No se detectaron montos ni comercio en el ticket",
                engine_used=engine_used,
            )

        # Si no se detectó monto, la confianza no puede ser alta
        confianza_final = min(confianza, 0.35) if monto is None else confianza

        return OCRResponse(
            success=True,
            monto=monto,
            subtotal=subtotal,
            tax=tax,
            line_amount=line_amount,
            payment_amount=payment_amount,
            rut=rut,
            document_type=document_type,
            fecha=fecha_parsed_local,
            comercio=comercio,
            items=items,
            currency=currency,
            texto_crudo=texto_crudo,
            confianza_ocr=confianza_final,
            extraction_confidence=extraction_confidence,
            arithmetic_consistent=arithmetic_consistent,
            engine_used=engine_used,
        )
    except Exception as e:
        logger.error("[OCR] Receipt processing error: %s", e)
        return OCRResponse(
            success=False,
            error=f"Error interno: {e}",
            engine_used="local-tesseract",
        )


_process_receipt_image = procesar_job_async


async def _execute_background_job(
    job_id: str, tmp_path: Path, engine: str = "auto"
) -> None:
    """Background worker for asynchronous OCR job execution."""
    try:
        job_store.update(job_id, status=JobStatus.PROCESSING)
        rec = job_store.get(job_id)
        if rec:
            rec.image_path = tmp_path
        result = await procesar_job_async(tmp_path, engine=engine)
        if result.success:
            job_store.update(job_id, status=JobStatus.COMPLETED, resultado=result)
        else:
            job_store.update(
                job_id,
                status=JobStatus.FAILED,
                resultado=result,
                error=result.error or "OCR processing failed",
            )
    except Exception as e:
        logger.exception("[JOB] Background processing failed for job %s: %s", job_id, e)
        job_store.update(job_id, status=JobStatus.FAILED, error=str(e))


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Service health check returning version and active jobs count."""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        active_jobs=job_store.active_jobs_count(),
    )


@app.post("/jobs", response_model=JobResponse, status_code=202)
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),  # noqa: B008
    engine: str = Form("auto"),
) -> JobResponse:
    """Submit an image for asynchronous OCR processing."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Solo imágenes")

    content = await file.read()
    if len(content) > settings.max_upload_size:
        max_mb = settings.max_upload_size // (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"Archivo excede {max_mb}MB",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    job = job_store.create()
    background_tasks.add_task(_execute_background_job, job.job_id, tmp_path, engine)

    return JobResponse(
        job_id=job.job_id,
        status=job.status,
        created_at=job.created_at,
    )


@app.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    """Retrieve status and result of an OCR job."""
    record = job_store.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(
        job_id=record.job_id,
        status=record.status,
        created_at=record.created_at,
        resultado=record.resultado,
        error=record.error,
    )


@app.get("/upload-form", response_class=HTMLResponse)
async def upload_form(
    session_id: str,
    familia_id: int = 1,
    engine: str = "auto",
) -> HTMLResponse:
    """Native HTML upload form with direct mobile camera capture."""
    safe_session_id = html_escape(session_id, quote=True)
    safe_familia_id = html_escape(str(familia_id), quote=True)
    safe_engine = html_escape(engine, quote=True)
    badge_class = "mode-local" if engine == "local" else "mode-cloud"
    mode_text = (
        "🔒 Modo Local (Privado)" if engine == "local" else "⚡ Modo Rápido (Cloud)"
    )
    html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Subir Ticket — Contador Oriental</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #f5f5f5;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      padding: 20px;
    }}
    .card {{
      background: white;
      border-radius: 12px;
      padding: 32px;
      max-width: 480px;
      width: 100%;
      box-shadow: 0 4px 24px rgba(0,0,0,0.08);
    }}
    h1 {{ font-size: 22px; margin-bottom: 8px; color: #1a1a1a; }}
    p {{ color: #666; font-size: 14px; margin-bottom: 16px; }}
    .mode-badge {{
      display: inline-block;
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 13px;
      font-weight: 600;
      margin-bottom: 20px;
    }}
    .mode-cloud {{
      background: #e3f2fd;
      color: #1565c0;
      border: 1px solid #90caf9;
    }}
    .mode-local {{
      background: #e8f5e9;
      color: #2e7d32;
      border: 1px solid #a5d6a7;
    }}
    .upload-area {{
      border: 2px dashed #2196F3;
      border-radius: 8px;
      padding: 32px;
      text-align: center;
      cursor: pointer;
      margin-bottom: 20px;
      transition: background 0.2s;
    }}
    .upload-area:hover {{ background: #e3f2fd; }}
    .upload-area svg {{
      width: 48px;
      height: 48px;
      color: #2196F3;
      margin-bottom: 12px;
    }}
    input[type=file] {{ display: none; }}

    .file-name {{ font-size: 13px; color: #333; margin-top: 8px; }}
    button {{
      width: 100%;
      padding: 14px;
      background: #2196F3;
      color: white;
      border: none;
      border-radius: 8px;
      font-size: 16px;
      cursor: pointer;
      transition: background 0.2s;
    }}
    button:hover {{ background: #1976D2; }}
    button:disabled {{ background: #90CAF9; cursor: not-allowed; }}
    .status {{
      margin-top: 16px;
      padding: 12px;
      border-radius: 8px;
      font-size: 14px;
      display: none;
    }}
    .status.loading {{ background: #e3f2fd; color: #1565C0; display: block; }}
    .status.success {{ background: #e8f5e9; color: #2E7D32; display: block; }}
    .status.error {{ background: #ffebee; color: #C62828; display: block; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>📸 Subir Ticket de Compra</h1>
    <p>Seleccioná la foto del ticket para extraer monto, fecha y comercio.</p>
    <div class="mode-badge {badge_class}">{mode_text}</div>

    <form id="form" enctype="multipart/form-data">
      <input type="hidden" name="session_id" value="{safe_session_id}">
      <input type="hidden" name="familia_id" value="{safe_familia_id}">
      <input type="hidden" name="engine" value="{safe_engine}">
      <input type="file" id="fileInput" name="file"
             accept="image/*" capture="environment">

      <div class="upload-area" onclick="document.getElementById('fileInput').click()">
        <svg viewBox="0 0 24 24" fill="none" stroke="#2196F3" stroke-width="1.5">
          <path stroke-linecap="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25
            2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"/>
        </svg>
        <div>Tocá para elegir o sacar una foto</div>
        <div class="file-name" id="fileName">JPG, PNG, WEBP, HEIC — máx 25MB</div>
      </div>

      <button type="submit" id="btn" disabled>Procesar ticket</button>
    </form>

    <div class="status" id="status"></div>
  </div>

  <script>
    const input = document.getElementById('fileInput');
    const btn = document.getElementById('btn');
    const fileName = document.getElementById('fileName');
    const status = document.getElementById('status');

    input.addEventListener('change', () => {{
      if (input.files && input.files[0]) {{
        fileName.textContent = input.files[0].name;
        btn.disabled = false;
      }}
    }});

    document.getElementById('form').addEventListener('submit', async (e) => {{
      e.preventDefault();
      btn.disabled = true;
      status.className = 'status loading';
      status.textContent = 'Procesando... esto puede tardar unos segundos.';

      const formData = new FormData(e.target);
      const p = window.location.pathname;
      const submitUrl = p.replace(/upload-form.*$/, 'upload-form-submit');
      try {{
        const resp = await fetch(submitUrl, {{
          method: 'POST',
          body: formData
        }});
        if (!resp.ok) {{
          const errBody = await resp.text();
          const detail = errBody.slice(0, 100) || 'Sin respuesta';
          throw new Error('Servidor error ' + resp.status + ': ' + detail);
        }}
        const data = await resp.json();
        if (data.success) {{
          status.className = 'status success';
          status.textContent =
            '\\u2705 Listo. Volv\\u00e9 a la app para ver los resultados.';
        }} else {{
          status.className = 'status error';
          status.textContent = 'Error: ' + (data.error || 'No se pudo procesar');
          btn.disabled = false;
        }}
      }} catch (err) {{
        status.className = 'status error';
        status.textContent = 'Error de red: ' + err.message;
        btn.disabled = false;
      }}
    }});
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html)


@app.post("/upload-form-submit")
async def upload_form_submit(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),  # noqa: B008
    session_id: str | None = Form(None),
    job_id: str | None = Form(None),
    familia_id: int = Form(1, gt=0),
    engine: str = Form("auto"),
) -> JSONResponse:
    """Process ticket upload from HTML form asynchronously."""
    if not file.content_type or not file.content_type.startswith("image/"):
        return JSONResponse(
            {"success": False, "error": "Solo imágenes"},
            status_code=400,
        )

    effective_id = session_id or job_id or str(uuid.uuid4())
    logger.info(
        "[FORM] Processing ticket session=%s familia=%d engine=%s",
        effective_id,
        familia_id,
        engine,
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        content = await file.read()
        if len(content) > settings.max_upload_size:
            max_mb = settings.max_upload_size // (1024 * 1024)
            return JSONResponse(
                {"success": False, "error": f"Archivo excede {max_mb}MB"},
                status_code=413,
            )
        tmp.write(content)
        tmp_path = Path(tmp.name)

    job_store.create(effective_id)
    job_store.set_family_job(familia_id, effective_id)
    job_store.update(effective_id, status=JobStatus.PROCESSING)
    background_tasks.add_task(_execute_background_job, effective_id, tmp_path, engine)

    return JSONResponse(
        {
            "success": True,
            "session_id": effective_id,
            "status": "processing",
            "message": "Imagen recibida, procesando en segundo plano",
        }
    )


@app.get("/resultado/{session_id}")
async def get_resultado(session_id: str) -> JSONResponse:
    """Polling endpoint for Flet: returns OCR result from memory when ready."""
    record = job_store.get(session_id)
    if record is None:
        return JSONResponse({"ready": False})

    if record.status == JobStatus.COMPLETED and record.resultado:
        data = record.resultado.model_dump(mode="json")
        return JSONResponse({"ready": True, **data})

    if record.status == JobStatus.FAILED:
        data = record.resultado.model_dump(mode="json") if record.resultado else {}
        return JSONResponse(
            {
                "ready": True,
                "success": False,
                "error": record.error or "No se pudo procesar el ticket",
                **data,
            }
        )

    return JSONResponse({"ready": False, "status": record.status.value})


@app.get("/pendiente/{familia_id}")
async def get_pendiente(familia_id: int) -> JSONResponse:
    """Check for pending results for a family to recover from tab suspensions."""
    record = job_store.get_family_job(familia_id)
    if record and record.resultado:
        data = record.resultado.model_dump(mode="json")
        return JSONResponse({"ready": True, "session_id": record.job_id, **data})
    return JSONResponse({"ready": False})


@app.post("/retry-cloud/{session_id}")
async def retry_cloud(
    session_id: str,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    """Re-process a previously uploaded ticket using Gemini Flash in the cloud."""
    record = job_store.get(session_id)
    if record is None or not record.image_path or not record.image_path.exists():
        return JSONResponse(
            {
                "success": False,
                "error": "Sesión o imagen expirada. Por favor re-subí el ticket.",
            },
            status_code=404,
        )

    job_store.update(session_id, status=JobStatus.PROCESSING)
    background_tasks.add_task(
        _execute_background_job, session_id, record.image_path, "gemini"
    )
    return JSONResponse(
        {
            "success": True,
            "session_id": session_id,
            "status": "processing",
            "message": "Reintentando con Gemini Flash en la nube",
        }
    )


@app.post("/upload-ocr", response_model=OCRResponse)
async def upload_ocr(
    file: UploadFile = File(...),  # noqa: B008
    familia_id: int = Form(..., gt=0),
    engine: str = Form("auto"),
) -> OCRResponse:
    """Synchronously process a receipt image with OCR."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Solo imágenes")

    logger.info(
        "Processing ticket synchronously for family %d (engine=%s)",
        familia_id,
        engine,
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        content = await file.read()
        if len(content) > settings.max_upload_size:
            max_mb = settings.max_upload_size // (1024 * 1024)
            raise HTTPException(status_code=413, detail=f"Archivo excede {max_mb}MB")
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        return await procesar_job_async(tmp_path, engine=engine)
    finally:
        _safe_unlink(tmp_path)


def main() -> None:
    """Start uvicorn server."""
    uvicorn.run(
        "ocr_api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
