"""
Modelo de dominio para ingresos familiares
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class IncomeCategory(str, Enum):
    """Categorías de ingresos"""

    SUELDO = "💼 Sueldo"
    JORNAL = "🔨 Jornal"
    EXTRA = "💰 Extra"
    BONO = "🎁 Bono"
    FREELANCE = "💻 Freelance"
    NEGOCIO = "🏪 Negocio"
    ALQUILER = "🏠 Alquiler"
    INVERSION = "📈 Inversión"
    JUBILADO = "👴 Jubilado/a"
    OTRO = "💵 Otro"


class RecurrenceFrequency(str, Enum):
    """Frecuencia de ingresos recurrentes"""

    DIARIA = "Diaria"
    SEMANAL = "Semanal"
    QUINCENAL = "Quincenal"
    MENSUAL = "Mensual"
    BIMESTRAL = "Bimestral"
    TRIMESTRAL = "Trimestral"
    SEMESTRAL = "Semestral"
    ANUAL = "Anual"


class Income(BaseModel):
    """
    Ingreso familiar
    Representa cualquier entrada de dinero al hogar
    """

    id: int | None = None

    # Relación con miembro de la familia
    family_member_id: int = Field(description="ID del miembro de la familia")

    # Datos básicos del ingreso
    monto: Decimal = Field(gt=0, description="Monto del ingreso")
    currency: str = Field(
        default="UYU", min_length=3, max_length=3, description="Moneda del ingreso"
    )
    fecha: date = Field(default_factory=date.today, description="Fecha del ingreso")
    descripcion: str = Field(
        min_length=1, max_length=200, description="Descripción del ingreso"
    )

    # Categorización
    categoria: IncomeCategory = Field(description="Categoría del ingreso")

    # Recurrencia
    es_recurrente: bool = Field(
        default=False, description="Indica si es un ingreso recurrente"
    )
    frecuencia: RecurrenceFrequency | None = Field(
        default=None, description="Frecuencia del ingreso recurrente"
    )

    # Información adicional
    notas: str | None = Field(
        default=None, max_length=500, description="Notas adicionales sobre el ingreso"
    )

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, value: str) -> str:
        value = value.upper()
        if value not in {"UYU", "USD"}:
            raise ValueError(f"Moneda no soportada: {value}")
        return value

    def __str__(self) -> str:
        if self.currency == "USD":
            return f"{self.categoria.value} - {self.descripcion}: USD {self.monto:.2f}"
        return f"{self.categoria.value} - {self.descripcion}: ${self.monto:.2f}"

    @property
    def categoria_nombre(self) -> str:
        """Nombre de la categoría sin emoji"""
        return (
            self.categoria.value.split(" ", 1)[1]
            if " " in self.categoria.value
            else self.categoria.value
        )
