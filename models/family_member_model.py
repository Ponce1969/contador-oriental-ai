"""
Modelo de dominio para miembros de la familia
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class IncomeType(str, Enum):
    """Tipo de ingreso del miembro de la familia"""
    FIJO = "Sueldo fijo"
    JORNALERO = "Jornalero"
    MIXTO = "Mixto"
    NINGUNO = "Sin ingresos"


class FamilyMember(BaseModel):
    """
    Miembro de la familia
    Representa a cada persona que forma parte del núcleo familiar
    """
    id: int | None = None
    
    # Datos básicos
    nombre: str = Field(min_length=1, max_length=100, description="Nombre del miembro")
    
    # Tipo de ingreso
    tipo_ingreso: IncomeType = Field(
        default=IncomeType.NINGUNO,
        description="Tipo de ingreso que recibe"
    )
    
    # Sueldo mensual fijo (si aplica)
    sueldo_mensual: float | None = Field(
        default=None,
        ge=0,
        description="Sueldo mensual fijo (solo para tipo FIJO o MIXTO)"
    )
    
    # Estado
    activo: bool = Field(
        default=True,
        description="Indica si el miembro está activo en el sistema"
    )
    
    # Notas
    notas: str | None = Field(
        default=None,
        max_length=500,
        description="Notas adicionales sobre el miembro"
    )
    
    def __str__(self) -> str:
        return f"{self.nombre} ({self.tipo_ingreso.value})"
    
    @property
    def tiene_sueldo_fijo(self) -> bool:
        """Indica si el miembro tiene sueldo fijo"""
        return self.tipo_ingreso in (IncomeType.FIJO, IncomeType.MIXTO)
    
    @property
    def es_jornalero(self) -> bool:
        """Indica si el miembro es jornalero"""
        return self.tipo_ingreso in (IncomeType.JORNALERO, IncomeType.MIXTO)
