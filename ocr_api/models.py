"""Data models for OCR microservice."""

from __future__ import annotations

from datetime import date, datetime  # noqa: TCH003
from decimal import Decimal  # noqa: TCH003
from enum import StrEnum

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    """Status of an OCR processing job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class OCRResponse(BaseModel):
    """OCR extraction response payload with strict Decimal monetary values."""

    success: bool
    monto: Decimal | None = None
    subtotal: Decimal | None = None
    tax: Decimal | None = None
    line_amount: Decimal | None = None
    payment_amount: Decimal | None = None
    comercio: str | None = None
    rut: str | None = None
    document_type: str | None = None
    fecha: date | None = None
    currency: str | None = None
    items: list[str] = Field(default_factory=list)
    categoria_sugerida: str | None = None
    subcategoria_sugerida: str | None = None
    extraction_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    confianza_ocr: float = Field(default=0.0, ge=0.0, le=1.0)
    total_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    merchant_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    date_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    arithmetic_consistent: bool | None = None
    texto_crudo: str = ""
    error: str | None = None
    engine_used: str = "local"


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
