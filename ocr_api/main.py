"""Microservicio OCR FastAPI."""

from __future__ import annotations

import json
import logging
import re
import tempfile
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import pytesseract
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageEnhance, ImageFilter
from result import Err

from ocr_api.config import settings
from ocr_api.models import HealthResponse, OCRResponse

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Prompt para Ollama/Gemma
_PROMPT_PARSEO = (
    "Analizá este texto de un ticket de compra uruguayo y extraé los datos.\n"
    "Respondé ÚNICAMENTE con un JSON válido, sin texto adicional, "
    "en este formato exacto:\n"
    "\n"
    "{{\n"
    '  "monto": 1250.0,\n'
    '  "fecha": "2026-02-28",\n'
    '  "comercio": "Tienda Inglesa",\n'
    '  "items": ["leche", "pan", "aceite"]\n'
    "}}\n"
    "\n"
    "Si no podés determinar un campo, usá null.\n"
    "La fecha debe estar en formato YYYY-MM-DD.\n"
    "El monto debe ser el TOTAL del ticket (número sin símbolos de moneda).\n"
    "\n"
    "Texto del ticket:\n"
    "{texto}"
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifecycle."""
    logger.info("🚀 OCR Service iniciado en puerto %d", settings.api_port)
    yield
    logger.info("👋 OCR Service detenido")


app = FastAPI(
    title="OCR API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def preprocesar_imagen(imagen: Image.Image) -> Image.Image:
    """Mejora la imagen antes de OCR."""
    imagen = imagen.convert("L")
    imagen = ImageEnhance.Contrast(imagen).enhance(2.0)
    imagen = imagen.filter(ImageFilter.SHARPEN)
    return imagen


async def extraer_texto_tesseract(imagen_path: Path) -> tuple[str, float]:
    """Extrae texto con Tesseract y retorna (texto, confianza)."""
    try:
        imagen = Image.open(imagen_path)
        imagen = preprocesar_imagen(imagen)

        datos = pytesseract.image_to_data(
            imagen,
            lang="spa",
            output_type=pytesseract.Output.DICT,
        )

        texto_crudo = " ".join(w for w in datos["text"] if w.strip())
        confs = [c for c in datos["conf"] if c > 0]
        confianza = round(sum(confs) / len(confs) / 100, 2) if confs else 0.0

        logger.info(
            "[OCR] Extraídos %d chars (confianza=%.2f)",
            len(texto_crudo),
            confianza,
        )
        return texto_crudo, confianza

    except Exception as e:
        logger.error("[OCR] Error en Tesseract: %s", e)
        return "", 0.0


async def parsear_con_ollama(texto: str) -> dict | None:
    """Parsea el texto con Ollama/Gemma."""
    if not texto.strip():
        return None

    try:
        prompt = _PROMPT_PARSEO.format(texto=texto[:1500])

        async with httpx.AsyncClient(timeout=30.0) as client:
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
            logger.warning("[PARSEO] Ollama devolvió respuesta vacía")
            return None

        # Buscar JSON en la respuesta
        match = re.search(r"\{.*?\}", respuesta, re.DOTALL)
        if not match:
            logger.warning("[PARSEO] No se encontró JSON en respuesta")
            return None

        datos = json.loads(match.group())
        logger.info(
            "[PARSEO] Parseado: comercio=%s monto=%s",
            datos.get("comercio"),
            datos.get("monto"),
        )
        return datos

    except Exception as e:
        logger.warning("[PARSEO] Error parseando con Ollama: %s", e)
        return None


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check."""
    return HealthResponse(status="ok", version="1.0.0")


@app.post("/upload-ocr", response_model=OCRResponse)
async def upload_ocr(
    file: UploadFile = File(...),
    familia_id: int = Form(..., gt=0),
) -> OCRResponse:
    """Procesar ticket con OCR."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Solo imágenes")

    logger.info("Procesando ticket para familia %d", familia_id)

    # Guardar archivo temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        # 1. Extraer texto con Tesseract
        texto_crudo, confianza = await extraer_texto_tesseract(tmp_path)

        if not texto_crudo or len(texto_crudo) < 20:
            return OCRResponse(
                success=False,
                error="No se pudo extraer texto de la imagen",
                confianza_ocr=confianza,
            )

        # 2. Parsear con Ollama
        parsed = await parsear_con_ollama(texto_crudo)

        if not parsed:
            return OCRResponse(
                success=True,
                texto_crudo=texto_crudo,
                confianza_ocr=confianza,
                error="OCR exitoso pero no se pudo parsear los datos",
            )

        # 3. Construir respuesta
        monto = parsed.get("monto")
        fecha_str = parsed.get("fecha")
        comercio = parsed.get("comercio")
        items = parsed.get("items") or []

        # Convertir fecha
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
            texto_crudo=texto_crudo,
            confianza_ocr=confianza,
        )

    except Exception as e:
        logger.error("[OCR] Error procesando ticket: %s", e)
        return OCRResponse(
            success=False,
            error=f"Error interno: {str(e)}",
        )
    finally:
        # Limpiar archivo temporal
        try:
            tmp_path.unlink()
        except Exception:
            pass


def main() -> None:
    """Iniciar servidor."""
    uvicorn.run(
        "ocr_api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
