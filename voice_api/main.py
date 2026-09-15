"""FastAPI Voice-to-Expense microservice."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape as html_escape
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING

import uvicorn
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from voice_api.config import settings
from voice_api.models import (
    HealthResponse,
    JobStatus,
    TranscribeResponse,
    VoiceExpenseResponse,
)
from voice_api.nlp import extract_expense_regex_fallback, parse_expense_with_ollama

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("uvicorn.error")


def _safe_unlink(path: Path) -> None:
    """Safely remove a temporary file ignoring filesystem errors."""
    with contextlib.suppress(OSError):
        os.unlink(path)


# ---------------------------------------------------------------------------
# Faster Whisper Singleton Engine
# ---------------------------------------------------------------------------

_whisper_engine = None
_whisper_lock = Lock()


def _get_whisper_model():
    """Singleton lazy thread-safe Faster Whisper engine with ARM64 thread limits."""
    global _whisper_engine
    if _whisper_engine is None:
        with _whisper_lock:
            if _whisper_engine is None:
                try:
                    from faster_whisper import WhisperModel

                    _whisper_engine = WhisperModel(
                        settings.whisper_model,
                        device="cpu",
                        compute_type=settings.whisper_compute_type,
                        cpu_threads=settings.whisper_threads,
                    )
                    logger.info(
                        "[VOICE] Faster-Whisper '%s' cargado (%d hilos)",
                        settings.whisper_model,
                        settings.whisper_threads,
                    )
                except Exception as e:
                    logger.error("[VOICE] Error inicializando WhisperModel: %s", e)
                    _whisper_engine = False
    return _whisper_engine if _whisper_engine is not False else None


def _run_transcription(audio_path: Path) -> tuple[str, str, float]:
    """Transcribe audio file in worker thread."""
    model = _get_whisper_model()
    if model is None:
        logger.warning("[VOICE] WhisperModel no disponible en este entorno")
        return "", "es", 0.0

    try:
        segments, info = model.transcribe(
            str(audio_path),
            language=settings.whisper_language,
            beam_size=3,
            vad_filter=True,
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        duration = float(getattr(info, "duration", 0.0))
        return text, str(info.language), duration
    except Exception as e:
        logger.error("[VOICE] Error durante la transcripción de audio: %s", e)
        return "", "es", 0.0


# ---------------------------------------------------------------------------
# In-Memory JobStore for Mobile Form Polling
# ---------------------------------------------------------------------------


@dataclass
class JobRecord:
    """In-memory record for an async voice processing job."""

    job_id: str
    status: JobStatus
    created_at: datetime
    resultado: VoiceExpenseResponse | None = None
    error: str | None = None


class JobStore:
    """Thread-safe in-memory store for voice jobs."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._lock = Lock()

    def create(self, job_id: str | None = None) -> JobRecord:
        jid = job_id or str(uuid.uuid4())
        record = JobRecord(
            job_id=jid,
            status=JobStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        with self._lock:
            self._jobs[jid] = record
        return record

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(
        self,
        job_id: str,
        status: JobStatus,
        resultado: VoiceExpenseResponse | None = None,
        error: str | None = None,
    ) -> JobRecord:
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
        now = datetime.now(UTC)
        with self._lock:
            expired = [
                jid
                for jid, rec in self._jobs.items()
                if (now - rec.created_at).total_seconds() > ttl_seconds
            ]
            for jid in expired:
                self._jobs.pop(jid, None)
            return len(expired)

    def active_jobs_count(self) -> int:
        with self._lock:
            return sum(
                1
                for rec in self._jobs.values()
                if rec.status in (JobStatus.PENDING, JobStatus.PROCESSING)
            )


job_store = JobStore()


async def _periodic_cleanup(ttl_seconds: int) -> None:
    """Periodically purge expired jobs from JobStore."""
    while True:
        try:
            await asyncio.sleep(60)
            purged = job_store.cleanup(ttl_seconds)
            if purged > 0:
                logger.info("[JobStore] Limpiados %d jobs de voz expirados", purged)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning("[JobStore] Error en limpieza periódica: %s", e)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Lifespan context manager for startup and cleanup."""
    logger.info("🚀 Voice Service iniciado en puerto %d", settings.api_port)
    asyncio.create_task(asyncio.to_thread(_get_whisper_model))

    cleanup_task = asyncio.create_task(_periodic_cleanup(settings.job_ttl_seconds))
    try:
        yield
    finally:
        cleanup_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await cleanup_task
        logger.info("🛑 Voice Service detenido")


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Contador Oriental — Voice Expense API",
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


async def process_voice_expense(audio_path: Path) -> VoiceExpenseResponse:
    """Full pipeline: Audio -> Faster-Whisper Text -> Ollama / Regex JSON."""
    total_start = time.perf_counter()

    # 1. Transcribir audio a texto
    stt_start = time.perf_counter()
    text, lang, duration = await asyncio.to_thread(_run_transcription, audio_path)
    transcription_time_ms = round((time.perf_counter() - stt_start) * 1000, 2)

    if not text:
        total_time_ms = round((time.perf_counter() - total_start) * 1000, 2)
        return VoiceExpenseResponse(
            success=False,
            text="",
            error="No se detectó voz ni audio comprensible",
            transcription_time_ms=transcription_time_ms,
            execution_time_ms=total_time_ms,
        )

    logger.info(
        "[VOICE] Transcrito (%s, %.1fs audio) en %.1fms: '%s'",
        lang,
        duration,
        transcription_time_ms,
        text,
    )

    # 2. Extracción semántica financiera con Ollama (o fallback regex)
    nlp_start = time.perf_counter()
    parsed = await parse_expense_with_ollama(text)
    if not parsed:
        logger.info("[VOICE] Ollama no disponible; usando extractor heurístico regex")
        parsed = extract_expense_regex_fallback(text)

    nlp_time_ms = round((time.perf_counter() - nlp_start) * 1000, 2)
    total_time_ms = round((time.perf_counter() - total_start) * 1000, 2)

    return VoiceExpenseResponse(
        success=True,
        text=text,
        monto=parsed.get("monto"),
        currency=parsed.get("currency", "UYU"),
        comercio=parsed.get("comercio"),
        categoria=parsed.get("categoria"),
        subcategoria=parsed.get("subcategoria"),
        medio_pago=parsed.get("medio_pago"),
        notas=parsed.get("notas") or text,
        confidence=parsed.get("confidence", 0.8),
        engine_used=f"faster-whisper+{parsed.get('engine_used', 'ollama')}",
        transcription_time_ms=transcription_time_ms,
        nlp_time_ms=nlp_time_ms,
        execution_time_ms=total_time_ms,
    )


async def _execute_background_voice_job(job_id: str, tmp_path: Path) -> None:
    """Worker en background para procesamiento de voz desde formulario web."""
    try:
        job_store.update(job_id, status=JobStatus.PROCESSING)
        result = await process_voice_expense(tmp_path)
        if result.success:
            job_store.update(job_id, status=JobStatus.COMPLETED, resultado=result)
        else:
            job_store.update(
                job_id,
                status=JobStatus.FAILED,
                resultado=result,
                error=result.error or "Error procesando audio",
            )
    except Exception as e:
        logger.exception("[VOICE] Error procesando job %s: %s", job_id, e)
        job_store.update(job_id, status=JobStatus.FAILED, error=str(e))
    finally:
        _safe_unlink(tmp_path)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Service health check."""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        model=settings.whisper_model,
        active_jobs=job_store.active_jobs_count(),
    )


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    file: UploadFile = File(...),  # noqa: B008
) -> TranscribeResponse:
    """Transcribe an audio file directly to plain text."""
    start_time = time.perf_counter()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        content = await file.read()
        if len(content) > settings.max_upload_size:
            max_mb = settings.max_upload_size // (1024 * 1024)
            raise HTTPException(status_code=413, detail=f"Audio excede {max_mb}MB")
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        text, lang, duration = await asyncio.to_thread(_run_transcription, tmp_path)
        exec_time = round((time.perf_counter() - start_time) * 1000, 2)
        return TranscribeResponse(
            success=bool(text),
            text=text,
            language=lang,
            duration_seconds=duration,
            execution_time_ms=exec_time,
            error=None if text else "No se detectó audio comprensible",
        )
    finally:
        _safe_unlink(tmp_path)


@app.post("/process-expense-voice", response_model=VoiceExpenseResponse)
async def process_expense_voice(
    file: UploadFile = File(...),  # noqa: B008
) -> VoiceExpenseResponse:
    """Synchronous pipeline: Audio -> Transcribe -> NLP Financial JSON."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        content = await file.read()
        if len(content) > settings.max_upload_size:
            max_mb = settings.max_upload_size // (1024 * 1024)
            raise HTTPException(status_code=413, detail=f"Audio excede {max_mb}MB")
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        return await process_voice_expense(tmp_path)
    finally:
        _safe_unlink(tmp_path)


@app.get("/voice-upload-form", response_class=HTMLResponse)
async def voice_upload_form(session_id: str) -> HTMLResponse:
    """Native HTML audio capture form with direct mobile microphone support."""
    safe_session_id = html_escape(session_id, quote=True)
    html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Grabar Gasto por Voz — Contador Oriental</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #0f172a;
      color: #f8fafc;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      padding: 20px;
    }}
    .card {{
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 16px;
      padding: 28px;
      max-width: 440px;
      width: 100%;
      box-shadow: 0 10px 25px -5px rgba(0,0,0,0.4);
      text-align: center;
    }}
    h1 {{ font-size: 20px; margin-bottom: 8px; color: #38bdf8; }}
    p {{ color: #94a3b8; font-size: 14px; margin-bottom: 20px; line-height: 1.5; }}
    .hint {{
      background: #0f172a;
      border-radius: 8px;
      padding: 12px;
      font-size: 13px;
      color: #cbd5e1;
      margin-bottom: 24px;
      border-left: 3px solid #38bdf8;
      text-align: left;
    }}
    .mic-btn {{
      width: 84px;
      height: 84px;
      border-radius: 50%;
      background: #0284c7;
      border: none;
      color: white;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 20px auto;
      box-shadow: 0 0 20px rgba(2, 132, 199, 0.4);
      transition: all 0.2s;
    }}
    .mic-btn:hover {{ background: #0369a1; transform: scale(1.05); }}
    .mic-btn.recording {{
      background: #ef4444;
      box-shadow: 0 0 25px rgba(239, 68, 68, 0.6);
      animation: pulse 1.5s infinite;
    }}
    @keyframes pulse {{
      0% {{ transform: scale(1); }}
      50% {{ transform: scale(1.08); }}
      100% {{ transform: scale(1); }}
    }}
    .status {{
      margin-top: 16px;
      padding: 12px;
      border-radius: 8px;
      font-size: 14px;
      display: none;
    }}
    .status.loading {{ background: #075985; color: #bae6fd; display: block; }}
    .status.success {{ background: #065f46; color: #a7f3d0; display: block; }}
    .status.error {{ background: #991b1b; color: #fecaca; display: block; }}
    .timer {{
      font-size: 18px;
      font-weight: bold;
      color: #38bdf8;
      margin-bottom: 12px;
    }}
    .native-upload {{
      margin-top: 24px;
      border-top: 1px solid #334155;
      padding-top: 16px;
    }}
    .native-upload label {{
      font-size: 12px;
      color: #94a3b8;
      cursor: pointer;
      text-decoration: underline;
    }}
  </style>
</head>
<body>
  <div class="card">
    <h1>🎙️ Grabar Gasto por Voz</h1>
    <p>Decí tu gasto con naturalidad.</p>
    <div class="hint">
      💬 <em>"Gasté 450 pesos en el Disco con la tarjeta Santander"</em><br>
      💬 <em>"Dos lucas de nafta en la Ancap en efectivo"</em>
    </div>

    <div class="timer" id="timer">00:00</div>
    <button class="mic-btn" id="recordBtn" title="Tocar para grabar">
      <svg width="36" height="36" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="2">
        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
        <line x1="12" x2="12" y1="19" y2="22"/>
      </svg>
    </button>
    <div id="btnLabel" style="font-size:14px; color:#cbd5e1; margin-bottom:16px;">
      Tocá para empezar a hablar
    </div>

    <div class="status" id="status"></div>

    <div class="native-upload">
      <label for="nativeInput">¿Problemas con el micrófono? Grabadora nativa</label>
      <input type="file" id="nativeInput" accept="audio/*"
             capture="microphone" style="display:none;">
    </div>
  </div>

  <script>
    let mediaRecorder = null;
    let audioChunks = [];
    let timerInterval = null;
    let seconds = 0;
    const session_id = "{safe_session_id}";

    const recordBtn = document.getElementById('recordBtn');
    const btnLabel = document.getElementById('btnLabel');
    const timer = document.getElementById('timer');
    const status = document.getElementById('status');
    const nativeInput = document.getElementById('nativeInput');

    function updateTimer() {{
      seconds++;
      const mins = String(Math.floor(seconds / 60)).padStart(2, '0');
      const secs = String(seconds % 60).padStart(2, '0');
      timer.textContent = mins + ':' + secs;
    }}

    async function sendAudio(blob) {{
      status.className = 'status loading';
      status.textContent = 'Transcribiendo audio y extrayendo gasto...';
      recordBtn.disabled = true;

      const formData = new FormData();
      formData.append('file', blob, 'voice_expense.webm');
      formData.append('session_id', session_id);
      const p = window.location.pathname;
      const submitUrl = p.replace(/voice-upload-form.*$/, 'voice-upload-submit');

      try {{
        const resp = await fetch(submitUrl, {{
          method: 'POST',
          body: formData
        }});
        const data = await resp.json();
        if (data.success) {{
          status.className = 'status success';
          status.textContent = '✅ Listo. Volvé a la app para confirmar el gasto.';
        }} else {{
          status.className = 'status error';
          status.textContent = 'Error: ' + (data.error || 'No se pudo procesar');
          recordBtn.disabled = false;
        }}
      }} catch (err) {{
        status.className = 'status error';
        status.textContent = 'Error de red: ' + err.message;
        recordBtn.disabled = false;
      }}
    }}

    recordBtn.addEventListener('click', async () => {{
      if (mediaRecorder && mediaRecorder.state === 'recording') {{
        mediaRecorder.stop();
        clearInterval(timerInterval);
        recordBtn.classList.remove('recording');
        btnLabel.textContent = 'Procesando...';
        return;
      }}

      try {{
        const stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        seconds = 0;
        timer.textContent = '00:00';
        timerInterval = setInterval(updateTimer, 1000);

        mediaRecorder.ondataavailable = e => {{
          if (e.data.size > 0) audioChunks.push(e.data);
        }};
        mediaRecorder.onstop = () => {{
          stream.getTracks().forEach(track => track.stop());
          const blob = new Blob(audioChunks, {{ type: 'audio/webm' }});
          sendAudio(blob);
        }};

        mediaRecorder.start();
        recordBtn.classList.add('recording');
        btnLabel.textContent = '🔴 Grabando... tocá de nuevo para terminar';
      }} catch (err) {{
        status.className = 'status error';
        status.textContent = 'Navegador bloqueó micrófono. Usá la opción de abajo.';
      }}
    }});

    nativeInput.addEventListener('change', () => {{
      if (nativeInput.files && nativeInput.files[0]) {{
        sendAudio(nativeInput.files[0]);
      }}
    }});
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html)


@app.post("/voice-upload-submit")
async def voice_upload_submit(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),  # noqa: B008
    session_id: str | None = Form(None),
) -> JSONResponse:
    """Submit voice audio from the HTML form asynchronously."""
    effective_id = session_id or str(uuid.uuid4())

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        content = await file.read()
        if len(content) > settings.max_upload_size:
            max_mb = settings.max_upload_size // (1024 * 1024)
            return JSONResponse(
                {"success": False, "error": f"Audio excede {max_mb}MB"},
                status_code=413,
            )
        tmp.write(content)
        tmp_path = Path(tmp.name)

    job_store.create(effective_id)
    job_store.update(effective_id, status=JobStatus.PROCESSING)
    background_tasks.add_task(_execute_background_voice_job, effective_id, tmp_path)

    return JSONResponse(
        {
            "success": True,
            "session_id": effective_id,
            "status": "processing",
            "message": "Audio recibido, procesando en segundo plano",
        }
    )


@app.get("/voice-resultado/{session_id}")
async def get_voice_resultado(session_id: str) -> JSONResponse:
    """Polling endpoint for Flet: returns voice extraction result when ready."""
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
                "error": record.error or "No se pudo procesar el audio",
                **data,
            }
        )

    return JSONResponse({"ready": False, "status": record.status.value})


def main() -> None:
    """Start uvicorn server for voice_api."""
    uvicorn.run(
        "voice_api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
