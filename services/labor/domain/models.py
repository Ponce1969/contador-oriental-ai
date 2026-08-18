"""
Modelos de dominio para el subdominio laboral y actividades económicas.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from services.labor.domain.enums import (
    ActivityNature,
    CalculationStatus,
    RemunerationType,
)


class DependentDetails(BaseModel):
    """Detalles especializados para trabajadores en relación de dependencia (MVP)."""

    id: int | None = None
    economic_activity_id: int | None = None
    remuneration_type: RemunerationType = RemunerationType.MENSUAL
    weekly_hours: int = 40
    estimated_monthly_nominal: Decimal | None = None


class EconomicActivity(BaseModel):
    """Actividad económica o relación laboral de un familiar (1:N)."""

    id: int | None = None
    familia_id: int = Field(description="ID de la familia (multi-tenant)")
    family_member_id: int = Field(description="ID del integrante familiar")
    nature: ActivityNature = Field(
        default=ActivityNature.DEPENDIENTE, description="Naturaleza de la actividad"
    )
    title: str = Field(
        default="Comercio / Servicios",
        max_length=100,
        description="Descripción del puesto o actividad",
    )
    start_date: date | None = Field(
        default=None, description="Fecha de alta / inicio de actividades (antigüedad)"
    )
    end_date: date | None = Field(
        default=None, description="Fecha de cese de la actividad (opcional)"
    )
    is_active: bool = Field(
        default=True, description="Indica si la actividad está vigente"
    )
    dependent_details: DependentDetails | None = Field(
        default=None, description="Detalles si es trabajador dependiente"
    )


class ComputableMonth(BaseModel):
    """Detalle de un mes computable dentro del período de cálculo."""

    year: int
    month: int
    monto: Decimal = Field(
        default=Decimal("0.00"), description="Monto computable en el mes"
    )
    es_proyectado: bool = Field(
        default=False,
        description="True si es una estimación de un mes que aún no transcurrió",
    )
    income_ids: list[int] = Field(
        default_factory=list,
        description="IDs de los Incomes reales computados en este mes",
    )


class CalculationRequest(BaseModel):
    """Parámetros de entrada para ejecutar un cálculo laboral determinístico."""

    familia_id: int
    family_member_id: int
    economic_activity_id: int
    calculation_type: str = Field(
        description="'AGUINALDO_JUNIO' | 'AGUINALDO_DICIEMBRE' | 'SALARIO_VACACIONAL'"
    )
    period_year: int
    period_semester: int = Field(description="1 (Junio) o 2 (Diciembre)")
    accrual_start: date
    accrual_end: date
    activity_start_date: date | None = None
    activity_end_date: date | None = None
    estimated_base_salary: Decimal | None = None
    registered_incomes: list[dict] = Field(
        default_factory=list,
        description="Ingresos reales registrados en el período",
    )

    requested_vacation_days: int = Field(
        default=20,
        ge=1,
        le=30,
        description="Días de licencia solicitados para salario vacacional",
    )


class CalculationResult(BaseModel):
    """Resultado inmutable y trazable producido por el motor de cálculo en Python."""

    request_summary: dict = Field(
        default_factory=dict, description="Resumen de metadata de la solicitud"
    )
    rule_version: str = Field(
        default="UY-MTSS-SAC-2026-v1",
        description="Identificador y versión de la regla aplicada",
    )
    status: CalculationStatus = Field(description="Estado del cálculo")
    currency: str = Field(default="UYU", description="Moneda del cálculo")
    input_income_ids: list[int] = Field(
        default_factory=list,
        description="IDs de los Incomes utilizados como base de cálculo",
    )
    months_breakdown: list[ComputableMonth] = Field(
        default_factory=list, description="Desglose mes a mes del semestre"
    )
    total_computable: Decimal = Field(
        default=Decimal("0.00"), description="Suma total de remuneraciones computables"
    )
    divisor: Decimal = Field(
        default=Decimal("12"),
        description="Divisor aplicado según ley (ej. 12 para aguinaldo)",
    )
    final_amount: Decimal = Field(
        default=Decimal("0.00"),
        description="Monto final calculado con precisión Decimal",
    )
    missing_fields: list[str] = Field(
        default_factory=list,
        description="Lista de campos faltantes si status == INSUFFICIENT_DATA",
    )
    explanation_notes: list[str] = Field(
        default_factory=list,
        description="Notas explicativas y fundamentos jurídicos de la regla",
    )
    calculated_at_utc: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp UTC del momento exacto del cálculo",
    )
