"""
Modelo de dominio para tracking de uso de IA
"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class AiUsage(BaseModel):
    """Registro de uso de IA por familia y día."""

    id: int | None = None
    familia_id: int
    date: date
    model: str = Field(
        description="Modelo usado: 'gemma2' o 'llama3'",
        pattern=r"^(gemma2|llama3)$",
    )
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=datetime.now)