"""
Modelo de dominio para cotizaciones de divisas
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ExchangeRate(BaseModel):
    """Cotización de divisa para un día específico"""

    id: int | None = None
    currency_pair: str = "USD/UYU"
    rate: Decimal = Field(gt=0, description="Cotización del dólar")
    date: date
    created_at: datetime = Field(default_factory=datetime.now)
