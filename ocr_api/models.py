"""Modelos Pydantic."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class OCRResponse(BaseModel):
    """Respuesta OCR."""

    success: bool
    monto: float | None = None
    comercio: str | None = None
    fecha: date | None = None
    items: list[str] = Field(default_factory=list)
    categoria_sugerida: str | None = None
    confianza_ocr: float = Field(default=0.0, ge=0.0, le=1.0)
    texto_crudo: str = ""
    error: str | None = None


class HealthResponse(BaseModel):
    """Health check."""

    status: str
    version: str
