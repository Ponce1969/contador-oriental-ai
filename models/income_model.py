"""
Modelo de dominio para ingresos familiares
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


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
    monto: float = Field(gt=0, description="Monto del ingreso en pesos")
    fecha: date = Field(default_factory=date.today, description="Fecha del ingreso")
    descripcion: str = Field(
        min_length=1,
        max_length=200,
        description="Descripción del ingreso"
    )
    
    # Categorización
    categoria: IncomeCategory = Field(description="Categoría del ingreso")
    
    # Recurrencia
    es_recurrente: bool = Field(
        default=False,
        description="Indica si es un ingreso recurrente"
    )
    frecuencia: RecurrenceFrequency | None = Field(
        default=None,
        description="Frecuencia del ingreso recurrente"
    )
    
    # Información adicional
    notas: str | None = Field(
        default=None,
        max_length=500,
        description="Notas adicionales sobre el ingreso"
    )
    
    def __str__(self) -> str:
        return f"{self.categoria.value} - {self.descripcion}: ${self.monto:.2f}"
    
    @property
    def categoria_nombre(self) -> str:
        """Nombre de la categoría sin emoji"""
        return self.categoria.value.split(" ", 1)[1] if " " in self.categoria.value else self.categoria.value
