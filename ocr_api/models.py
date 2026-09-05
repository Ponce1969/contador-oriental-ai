"""Data models for OCR microservice."""

from __future__ import annotations

from datetime import date, datetime  # noqa: TCH003
from enum import StrEnum

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    """Status of an OCR processing job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class OCRResponse(BaseModel):
    """OCR extraction response payload."""

    success: bool
    monto: float | None = None
    comercio: str | None = None
    fecha: date | None = None
    currency: str | None = None
    items: list[str] = Field(default_factory=list)
    categoria_sugerida: str | None = None
    confianza_ocr: float = Field(default=0.0, ge=0.0, le=1.0)
    texto_crudo: str = ""
    error: str | None = None


class JobResponse(BaseModel):
    """Job status and result response."""

    job_id: str
    status: JobStatus
    created_at: datetime
    resultado: OCRResponse | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    """Service health check response."""

    status: str
    version: str
    active_jobs: int = 0
