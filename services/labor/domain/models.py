"""
Modelos de dominio para el subdominio laboral y actividades económicas.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from services.labor.domain.dtos import (
    CalculableIncomeDTO,
    EligibilityEvaluation,
    IASSPayload,
    IndependentProfile,
    LiteralEPayload,
    MonotributoPayload,
    PensionProfile,
    PersonalServicesPayload,
)
from services.labor.domain.enums import (
    ActivityNature,
    CalculationMode,
    CalculationStatus,
    EstimationAccuracy,
    FonasaBeneficiaryType,
    RemunerationType,
)

__all__ = [
    "TaxProfile",
    "DependentDetails",
    "IndependentProfile",
    "PensionProfile",
    "EconomicActivity",
    "ComputableMonth",
    "CalculableIncomeDTO",
    "EligibilityEvaluation",
    "PersonalServicesPayload",
    "LiteralEPayload",
    "MonotributoPayload",
    "IASSPayload",
    "CalculationRequest",
    "CalculationResult",
    "NominalEstimationResult",
]


class TaxProfile(BaseModel):
    """Atributos personales y familiares del contribuyente para cargas y retenciones."""

    children_count: int = Field(default=0, ge=0, description="Hijos menores a cargo")
    disabled_children_count: int = Field(
        default=0, ge=0, description="Hijos con discapacidad a cargo"
    )
    has_spouse_charge: bool = Field(
        default=False, description="Cónyuge o concubino a cargo sin cobertura propia"
    )
    child_deduction_share: Decimal = Field(
        default=Decimal("1.0"),
        ge=Decimal("0.0"),
        le=Decimal("1.0"),
        description="Porcentaje de atribución de la deducción por hijos (100% o 50%)",
    )
    fonasa_type: FonasaBeneficiaryType = Field(
        default=FonasaBeneficiaryType.SINGLE_NO_CHILDREN,
        description="Categoría familiar de cobertura FONASA",
    )


class DependentDetails(BaseModel):
    """Detalles especializados para trabajadores en relación de dependencia (MVP)."""

    id: int | None = None
    economic_activity_id: int | None = None
    remuneration_type: RemunerationType = RemunerationType.MENSUAL
    weekly_hours: int = 40
    estimated_monthly_nominal: Decimal | None = None
    tax_profile: TaxProfile = Field(default_factory=TaxProfile)


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
    independent_profile: IndependentProfile | None = Field(
        default=None, description="Detalles si es trabajador independiente (Fase 3)"
    )
    pension_profile: PensionProfile | None = Field(
        default=None, description="Detalles si es pasivo o jubilado (Fase 3)"
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
    """Parámetros de entrada inmutables para cualquier cómputo del motor laboral."""

    familia_id: int
    family_member_id: int
    economic_activity_id: int
    mode: CalculationMode = CalculationMode.AGUINALDO
    calculation_type: str = Field(
        default="AGUINALDO_JUNIO",
        description="Tipo de cálculo laboral solicitado",
    )
    period_year: int
    period_semester: int = Field(default=1, description="1 (Junio) o 2 (Diciembre)")
    accrual_start: date = Field(default_factory=date.today)
    accrual_end: date = Field(default_factory=date.today)
    activity_start_date: date | None = None
    activity_end_date: date | None = None
    estimated_base_salary: Decimal | None = None
    tax_profile: TaxProfile = Field(default_factory=TaxProfile)
    registered_incomes: list[Any] = Field(
        default_factory=list,
        description="Ingresos reales registrados en el período",
    )
    requested_vacation_days: int = Field(
        default=20,
        ge=1,
        le=30,
        description="Días de licencia solicitados para salario vacacional",
    )
    nominal_amount: Decimal | None = None
    target_liquid_amount: Decimal | None = None

    # Parámetros para Servicios Personales (Fase 3A)
    independent_profile: IndependentProfile | None = None
    bimonthly_billed_without_vat: Decimal | None = None
    is_client_cede: bool = False
    vat_rate_type: str = "BASIC"
    actual_documented_expenses: Decimal | None = None


class CalculationResult(BaseModel):
    """Resultado inmutable, auditable y trazable producido por el motor en Python."""

    request_summary: dict[str, Any] = Field(
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
        default_factory=list, description="Desglose mes a mes del período"
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

    # Desglose de Retenciones e Impuestos (Dependientes - Fase 2)
    nominal_amount: Decimal = Decimal("0.00")
    montepio_amount: Decimal = Decimal("0.00")
    frl_amount: Decimal = Decimal("0.00")
    fonasa_amount: Decimal = Decimal("0.00")
    fonasa_effective_rate: Decimal = Decimal("0.0000")
    total_social_security: Decimal = Decimal("0.00")
    irpf_gross_tax: Decimal = Decimal("0.00")
    irpf_deductions_amount: Decimal = Decimal("0.00")
    irpf_net_withholding: Decimal = Decimal("0.00")
    irpf_marginal_rate: Decimal = Decimal("0.0000")
    total_withholdings: Decimal = Decimal("0.00")
    liquid_amount: Decimal = Decimal("0.00")

    # Diagnóstico y trazabilidad
    missing_fields: list[str] = Field(
        default_factory=list,
        description="Lista de campos faltantes si status == INSUFFICIENT_DATA",
    )
    missing_information: list[str] = Field(default_factory=list)
    review_reasons: list[str] = Field(default_factory=list)
    legal_references: list[str] = Field(default_factory=list)
    explanation_notes: list[str] = Field(
        default_factory=list,
        description="Notas explicativas y fundamentos jurídicos de la regla",
    )
    calculated_at_utc: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp UTC del momento exacto del cálculo",
    )

    # Fase 3: Elegibilidad y Payloads Especializados
    eligibility: EligibilityEvaluation | None = None
    personal_services_payload: PersonalServicesPayload | None = None
    literal_e_payload: LiteralEPayload | None = None
    monotributo_payload: MonotributoPayload | None = None
    iass_payload: IASSPayload | None = None
    independent_profile: IndependentProfile | None = None
    pension_profile: PensionProfile | None = None


class NominalEstimationResult(BaseModel):
    """Resultado estructurado del cálculo inverso determinístico."""

    status: EstimationAccuracy
    requested_liquid: Decimal
    estimated_nominal: Decimal
    resulting_liquid: Decimal
    difference: Decimal
    tolerance: Decimal = Decimal("0.01")
    iterations_used: int
    withholdings_breakdown: CalculationResult
