"""
Modelo de dominio para ingresos familiares
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class IncomeCategory(StrEnum):
    """Categorías de ingresos adaptadas a la realidad tributaria y laboral uruguaya."""

    SUELDO = "💼 Sueldo"
    JORNAL = "🔨 Jornal"
    EXTRA = "💰 Extra"
    BONO = "🎁 Bono"
    INDEPENDIENTE = "🛠️ Independiente / Unipersonal"
    NEGOCIO = "🏪 Negocio"
    ALQUILER = "🏠 Alquiler"
    INVERSION = "📈 Inversión"
    JUBILACION_PENSION = "👴 Jubilación / Pensión"
    OTRO = "💵 Otro"

    # Categorías rurales / campo
    VENTA_GANADO = "🐄 Venta de Ganado"
    VENTA_GRANOS = "🌾 Venta de Granos / Cosecha"
    VENTA_LANA_LECHE = "🥛 Venta de Leche / Lana"
    SERVICIOS_AGRO = "🚜 Servicios Rurales / Maquinaria"
    OTRO_RURAL = "🌾 Otro Ingreso Campo"

    # Alias de compatibilidad hacia atrás
    FREELANCE = "🛠️ Independiente / Unipersonal"
    JUBILADO = "👴 Jubilación / Pensión"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            val_lower = value.lower()
            if (
                "freelance" in val_lower
                or "independiente" in val_lower
                or "unipersonal" in val_lower
            ):
                return cls.INDEPENDIENTE
            if "jubilad" in val_lower or "pension" in val_lower:
                return cls.JUBILACION_PENSION
        return None


class RecurrenceFrequency(StrEnum):
    """Frecuencia de ingresos recurrentes"""

    DIARIA = "Diaria"
    SEMANAL = "Semanal"
    QUINCENAL = "Quincenal"
    MENSUAL = "Mensual"
    BIMESTRAL = "Bimestral"
    TRIMESTRAL = "Trimestral"
    SEMESTRAL = "Semestral"
    ANUAL = "Anual"


INCOME_CATEGORIES_HOGAR: list[IncomeCategory] = [
    IncomeCategory.SUELDO,
    IncomeCategory.JORNAL,
    IncomeCategory.EXTRA,
    IncomeCategory.BONO,
    IncomeCategory.INDEPENDIENTE,
    IncomeCategory.NEGOCIO,
    IncomeCategory.ALQUILER,
    IncomeCategory.INVERSION,
    IncomeCategory.JUBILACION_PENSION,
    IncomeCategory.OTRO,
]

INCOME_CATEGORIES_CAMPO: list[IncomeCategory] = [
    IncomeCategory.VENTA_GANADO,
    IncomeCategory.VENTA_GRANOS,
    IncomeCategory.VENTA_LANA_LECHE,
    IncomeCategory.SERVICIOS_AGRO,
    IncomeCategory.OTRO_RURAL,
]


def get_income_categories_for_entorno(
    entorno: str | None = "hogar",
) -> list[IncomeCategory]:
    """Retorna las categorías de ingresos según el entorno (hogar, campo o todas)."""
    if entorno == "campo":
        return INCOME_CATEGORIES_CAMPO
    if entorno in ("consolidado", "all", None):
        return list(IncomeCategory)
    return INCOME_CATEGORIES_HOGAR


class Income(BaseModel):
    """
    Ingreso familiar
    Representa cualquier entrada de dinero al hogar
    """

    id: int | None = None

    # Relación con miembro de la familia
    family_member_id: int = Field(description="ID del miembro de la familia")
    economic_activity_id: int | None = Field(
        default=None, description="ID de la actividad económica asociada (opcional)"
    )

    # Concepto laboral / financiero
    concept: str | None = Field(
        default=None, description="Concepto laboral/financiero (salary, overtime, etc.)"
    )

    # Datos básicos del ingreso
    monto: Decimal = Field(gt=0, description="Monto del ingreso")
    currency: str = Field(
        default="UYU", min_length=3, max_length=3, description="Moneda del ingreso"
    )
    fecha: date = Field(default_factory=date.today, description="Fecha del ingreso")
    descripcion: str = Field(
        min_length=1, max_length=200, description="Descripción del ingreso"
    )

    # Categorización y Entorno
    categoria: IncomeCategory = Field(description="Categoría del ingreso")
    entorno: str = Field(
        default="hogar", description="Entorno o centro de costo: hogar | campo"
    )

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
