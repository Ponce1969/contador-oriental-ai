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
    compra: Decimal = Field(gt=0, description="Cotización de compra del dólar")
    venta: Decimal = Field(gt=0, description="Cotización de venta del dólar")
    date: date
    created_at: datetime = Field(default_factory=datetime.now)
