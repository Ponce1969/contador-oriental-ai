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
from fastapi.responses import HTMLResponse, JSONResponse
from PIL import Image, ImageEnhance, ImageFilter

from ocr_api.config import settings
from ocr_api.models import HealthResponse, OCRResponse

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# Almacenamiento en memoria: session_id -> OCRResponse (TTL implicito por restart)
_resultados: dict[str, dict] = {}

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


@app.get("/upload-form", response_class=HTMLResponse)
async def upload_form(session_id: str, familia_id: int = 1) -> HTMLResponse:
    """Formulario HTML nativo para subir ticket — no depende de FilePicker."""
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
    .upload-area svg {{ width: 48px; height: 48px; color: #2196F3; margin-bottom: 12px; }}
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
      <input type="hidden" name="session_id" value="{session_id}">
      <input type="hidden" name="familia_id" value="{familia_id}">
      <input type="file" id="fileInput" name="file" accept="image/*">

      <div class="upload-area" onclick="document.getElementById('fileInput').click()">
        <svg viewBox="0 0 24 24" fill="none" stroke="#2196F3" stroke-width="1.5">
          <path stroke-linecap="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25
            2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"/>
        </svg>
        <div>Tocá para elegir una foto</div>
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
      if (input.files[0]) {{
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
          status.textContent = '\u2705 Listo. Volvé a la app para ver los resultados.';
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
    file: UploadFile = File(...),
    session_id: str = Form(...),
    familia_id: int = Form(1, gt=0),
) -> JSONResponse:
    """Recibe el archivo del formulario HTML, procesa OCR y guarda resultado."""
    if not file.content_type or not file.content_type.startswith("image/"):
        return JSONResponse({"success": False, "error": "Solo imágenes"}, status_code=400)

    logger.info("[FORM] Procesando ticket session=%s familia=%d", session_id, familia_id)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        texto_crudo, confianza = await extraer_texto_tesseract(tmp_path)

        if not texto_crudo or len(texto_crudo) < 20:
            result = {"success": False, "error": "No se pudo extraer texto",
                      "confianza_ocr": confianza}
            _resultados[session_id] = result
            return JSONResponse(result)

        parsed = await parsear_con_ollama(texto_crudo)

        fecha_str = (parsed or {}).get("fecha")
        fecha_iso: str | None = None
        if fecha_str:
            try:
                fecha_iso = date.fromisoformat(fecha_str).isoformat()
            except (ValueError, TypeError):
                pass

        result = {
            "success": True,
            "monto": (parsed or {}).get("monto"),
            "fecha": fecha_iso,
            "comercio": (parsed or {}).get("comercio"),
            "items": (parsed or {}).get("items") or [],
            "confianza_ocr": confianza,
            "texto_crudo": texto_crudo,
        }
        _resultados[session_id] = result
        logger.info("[FORM] Resultado guardado session=%s", session_id)
        return JSONResponse(result)

    except Exception as e:
        logger.error("[FORM] Error: %s", e)
        result = {"success": False, "error": str(e)}
        _resultados[session_id] = result
        return JSONResponse(result, status_code=500)
    finally:
        try:
            tmp_path.unlink()
        except Exception:
            pass


@app.get("/resultado/{session_id}")
async def get_resultado(session_id: str) -> JSONResponse:
    """Polling desde Flet: retorna el resultado OCR cuando esté listo."""
    if session_id not in _resultados:
        return JSONResponse({"ready": False})
    data = _resultados.pop(session_id)  # consume una sola vez
    return JSONResponse({"ready": True, **data})


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
