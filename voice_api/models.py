"""Data models for Voice-to-Expense microservice."""

from __future__ import annotations

from datetime import datetime  # noqa: TCH003
from decimal import Decimal  # noqa: TCH003
from enum import StrEnum

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    """Status of an audio processing job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TranscribeResponse(BaseModel):
    """Response payload for audio transcription."""

    success: bool
    text: str = ""
    language: str = "es"
    duration_seconds: float = 0.0
    execution_time_ms: float = 0.0
    error: str | None = None


class VoiceExpenseResponse(BaseModel):
    """Response payload with extracted financial fields from voice audio."""

    success: bool
    text: str = ""
    monto: Decimal | None = None
    currency: str = "UYU"
    comercio: str | None = None
    categoria: str | None = None
    subcategoria: str | None = None
    medio_pago: str | None = None
    notas: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    engine_used: str = "whisper-base"
    transcription_time_ms: float = 0.0
    nlp_time_ms: float = 0.0
    execution_time_ms: float = 0.0
    error: str | None = None


class JobResponse(BaseModel):
    """Job status and result response for async polling."""

    job_id: str
    status: JobStatus
    created_at: datetime
    resultado: VoiceExpenseResponse | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    """Service health check response."""

    status: str
    version: str
    model: str
    active_jobs: int = 0
