"""FastAPI OCR microservice."""

from __future__ import annotations

import asyncio
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
from html import escape as html_escape
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING

import cv2  # type: ignore[import-not-found]
import httpx
import numpy as np
import pytesseract
import uvicorn
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from PIL import Image

from ocr_api.config import settings
from ocr_api.models import HealthResponse, JobResponse, JobStatus, OCRResponse

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


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


class JobStore:
    """Thread-safe in-memory job store with TTL eviction."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._lock = Lock()

    def create(self, job_id: str | None = None) -> JobRecord:
        """Create a new job entry with PENDING status."""
        with self._lock:
            jid = job_id or str(uuid.uuid4())
            record = JobRecord(
                job_id=jid,
                status=JobStatus.PENDING,
                created_at=datetime.now(UTC),
            )
            self._jobs[jid] = record
            return record

    def get(self, job_id: str) -> JobRecord | None:
        """Retrieve a job by its ID."""
        with self._lock:
            return self._jobs.get(job_id)

    def update(
        self,
        job_id: str,
        status: JobStatus,
        resultado: OCRResponse | None = None,
        error: str | None = None,
    ) -> JobRecord:
        """Update job status and results."""
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
                del self._jobs[jid]
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


_PROMPT_PARSEO = (
    "Analizá este texto de un ticket de compra uruguayo y extraé los datos.\n"
    "Respondé ÚNICAMENTE con un JSON válido, sin texto adicional, "
    "en este formato exacto:\n"
    "\n"
    "{{\n"
    '  "monto": 1250.0,\n'
    '  "fecha": "2026-02-28",\n'
    '  "comercio": "Tienda Inglesa",\n'
    '  "items": ["leche", "pan", "aceite"],\n'
    '  "currency": null\n'
    "}}\n"
    "\n"
    "Si no podés determinar un campo, usá null.\n"
    "La fecha debe estar en formato YYYY-MM-DD.\n"
    "El monto debe ser el TOTAL del ticket (número sin símbolos de moneda).\n"
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
    allow_origins=[os.getenv("OCR_ALLOWED_ORIGIN", "http://app:8550")],
    allow_credentials=False,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


# ---------------------------------------------------------------------------
# Image Preprocessing & OCR Extraction
# ---------------------------------------------------------------------------


def preprocesar_imagen(imagen: Image.Image) -> Image.Image:
    """Preprocess receipt image optimized for ARM / Orange Pi 5 Plus.

    - Convert to grayscale.
    - Smart resize: ONLY downscale if max(h, w) > 1920 using cv2.INTER_AREA.
      Never upscale with fx=2.
    - CLAHE + GaussianBlur + adaptiveThreshold.
    - Avoid heavy cubic warp affine transformations.
    """
    img = np.array(imagen)
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    h, w = img.shape[:2]
    max_dim = max(h, w)
    if max_dim > 1920:
        scale = 1920.0 / max_dim
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    img = clahe.apply(img)
    img = cv2.GaussianBlur(img, (3, 3), 0)
    img = cv2.adaptiveThreshold(
        img,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        2,
    )
    return Image.fromarray(img)


def _run_tesseract(imagen_path: Path) -> tuple[str, float]:
    """Synchronously run preprocessing and Tesseract OCR."""
    with Image.open(imagen_path) as img:
        imagen = preprocesar_imagen(img)

    datos = pytesseract.image_to_data(
        imagen,
        lang="spa",
        config="--psm 6 --oem 3",
        output_type=pytesseract.Output.DICT,
    )

    texto_crudo = " ".join(w for w in datos["text"] if w.strip())
    confs = [int(c) for c in datos["conf"] if str(c).strip() not in ("-1", "")]
    confianza = round(sum(confs) / len(confs) / 100, 2) if confs else 0.0
    return texto_crudo, confianza


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


async def parsear_con_ollama(texto: str) -> dict | None:
    """Parse raw OCR text using Ollama/Gemma with 60s timeout."""
    if not texto.strip():
        return None

    try:
        prompt = _PROMPT_PARSEO.format(texto=texto[:1500])

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                },
            )
            response.raise_for_status()
            respuesta = response.json().get("response", "")

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
        logger.warning("[PARSER] Ollama extraction failed: %s", e)
        return None


async def _process_receipt_image(tmp_path: Path) -> OCRResponse:
    """Process a single receipt image via Tesseract and Ollama."""
    try:
        texto_crudo, confianza = await extraer_texto_tesseract(tmp_path)
        if not texto_crudo or len(texto_crudo) < 20:
            return OCRResponse(
                success=False,
                error="No se pudo extraer texto de la imagen",
                confianza_ocr=confianza,
            )

        parsed = await parsear_con_ollama(texto_crudo)
        if not parsed:
            return OCRResponse(
                success=True,
                texto_crudo=texto_crudo,
                confianza_ocr=confianza,
                error="OCR exitoso pero no se pudo parsear los datos",
            )

        monto = parsed.get("monto")
        fecha_str = parsed.get("fecha")
        comercio = _str_or_none(parsed.get("comercio"))
        items = parsed.get("items") or []
        currency = _resolve_currency(parsed.get("currency"))

        fecha_parsed: date | None = None
        if fecha_str:
            try:
                fecha_parsed = date.fromisoformat(fecha_str)
            except (ValueError, TypeError):
                pass

        return OCRResponse(
            success=True,
            monto=monto,
            fecha=fecha_parsed,
            comercio=comercio,
            items=items,
            currency=currency,
            texto_crudo=texto_crudo,
            confianza_ocr=confianza,
        )
    except Exception as e:
        logger.error("[OCR] Receipt processing error: %s", e)
        return OCRResponse(
            success=False,
            error=f"Error interno: {e}",
        )


async def _execute_background_job(job_id: str, tmp_path: Path) -> None:
    """Background worker for asynchronous OCR job execution."""
    try:
        job_store.update(job_id, status=JobStatus.PROCESSING)
        result = await _process_receipt_image(tmp_path)
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
    finally:
        _safe_unlink(tmp_path)


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
    background_tasks.add_task(_execute_background_job, job.job_id, tmp_path)

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
async def upload_form(session_id: str, familia_id: int = 1) -> HTMLResponse:
    """Native HTML upload form with direct mobile camera capture."""
    safe_session_id = html_escape(session_id, quote=True)
    safe_familia_id = html_escape(str(familia_id), quote=True)
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
    p {{ color: #666; font-size: 14px; margin-bottom: 24px; }}
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

    <form id="form" enctype="multipart/form-data">
      <input type="hidden" name="session_id" value="{safe_session_id}">
      <input type="hidden" name="familia_id" value="{safe_familia_id}">
      <input type="file" id="fileInput" name="file"
             accept="image/*" capture="environment">

      <div class="upload-area" onclick="document.getElementById('fileInput').click()">
        <svg viewBox="0 0 24 24" fill="none" stroke="#2196F3" stroke-width="1.5">
          <path stroke-linecap="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25
            2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"/>
        </svg>
        <div>Tocá para elegir o sacar una foto</div>
        <div class="file-name" id="fileName">JPG, PNG, WEBP — máx 10MB</div>
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
      try {{
        const resp = await fetch('/upload-form-submit', {{
          method: 'POST',
          body: formData
        }});
        const data = await resp.json();
        if (data.success) {{
          status.className = 'status success';
          status.textContent = '\\u2705 Listo. Volvé a la app para ver los resultados.';
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
    file: UploadFile = File(...),  # noqa: B008
    session_id: str | None = Form(None),
    job_id: str | None = Form(None),
    familia_id: int = Form(1, gt=0),
) -> JSONResponse:
    """Process ticket submission from HTML form and store result in memory."""
    if not file.content_type or not file.content_type.startswith("image/"):
        return JSONResponse(
            {"success": False, "error": "Solo imágenes"},
            status_code=400,
        )

    effective_id = session_id or job_id or str(uuid.uuid4())
    logger.info(
        "[FORM] Processing ticket session=%s familia=%d",
        effective_id,
        familia_id,
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
    job_store.update(effective_id, status=JobStatus.PROCESSING)

    try:
        result = await _process_receipt_image(tmp_path)
        if result.success:
            job_store.update(effective_id, status=JobStatus.COMPLETED, resultado=result)
        else:
            job_store.update(
                effective_id,
                status=JobStatus.FAILED,
                resultado=result,
                error=result.error or "OCR extraction failed",
            )
        return JSONResponse(result.model_dump(mode="json"))

    except Exception as e:
        logger.error("[FORM] Error: %s", e)
        err_res = OCRResponse(success=False, error=str(e))
        job_store.update(
            effective_id,
            status=JobStatus.FAILED,
            resultado=err_res,
            error=str(e),
        )
        return JSONResponse(err_res.model_dump(mode="json"), status_code=500)
    finally:
        _safe_unlink(tmp_path)


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

    return JSONResponse({"ready": False})


@app.get("/pendiente/{familia_id}")
async def get_pendiente(familia_id: int) -> JSONResponse:
    """Check for pending session results for a family.

    Always returns ready: False in stateless RAM mode, avoiding errors if Flet calls it.
    """
    return JSONResponse({"ready": False})


@app.post("/upload-ocr", response_model=OCRResponse)
async def upload_ocr(
    file: UploadFile = File(...),  # noqa: B008
    familia_id: int = Form(..., gt=0),
) -> OCRResponse:
    """Synchronously process a receipt image with OCR."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Solo imágenes")

    logger.info("Processing ticket synchronously for family %d", familia_id)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        content = await file.read()
        if len(content) > settings.max_upload_size:
            max_mb = settings.max_upload_size // (1024 * 1024)
            raise HTTPException(status_code=413, detail=f"Archivo excede {max_mb}MB")
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        return await _process_receipt_image(tmp_path)
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
