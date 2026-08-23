"""
DTOs tipados para cálculos laborales, tributarios e independientes en Uruguay.
Garantiza 0 Any, tipado estricto e inmutabilidad.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from services.labor.domain.enums import (
    EligibilityStatus,
    IncomeConcept,
    IndependentTaxRegime,
    PensionFundType,
)


class CalculableIncomeDTO(BaseModel):
    """Representación inmutable de un ingreso computable para el motor."""

    income_id: int | None = None
    amount_nominal: Decimal = Field(
        gt=Decimal("0.00"), description="Monto en moneda de origen"
    )
    amount_currency: str = Field(default="UYU", max_length=3)
    accrual_date: date
    concept: IncomeConcept
    economic_activity_id: int | None = None
    is_projected: bool = False
    vat_rate_applied: Decimal | None = None
    withholding_irpf_deducted: Decimal = Decimal("0.00")
    withholding_iva_deducted: Decimal = Decimal("0.00")


class EligibilityEvaluation(BaseModel):
    """Resultado formal de la evaluación de elegibilidad de un régimen."""

    status: EligibilityStatus
    violations: list[str] = Field(default_factory=list)
    review_reasons: list[str] = Field(default_factory=list)
    can_proceed_to_calculation: bool = True


class IndependentProfile(BaseModel):
    """Hechos declarados por el contribuyente independiente (sin alícuotas fijadas)."""

    id: int | None = None
    economic_activity_id: int | None = None
    regime: IndependentTaxRegime = IndependentTaxRegime.SERVICIOS_PERSONALES
    pension_fund: PensionFundType | None = None
    activity_code: str | None = None
    is_professional: bool | None = None
    cjppu_category: int | None = None
    has_mides_certificate: bool | None = None
    mides_certificate_expiry: date | None = None
    local_premises_sqm: Decimal | None = None
    partner_count: int | None = None
    employees_count: int = 0
    estimated_monthly_gross_sales: Decimal | None = None
    billing_includes_iva: bool | None = None
    opt_for_actual_expenses: bool = False
    regime_start_date: date | None = None


class PensionProfile(BaseModel):
    """Perfil previsional de pasivo / jubilado / pensionista (Fase 3D)."""

    pension_fund: PensionFundType = PensionFundType.BPS
    monthly_pension_nominal: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0.00")
    )
    has_fonasa_coverage: bool = True
    fonasa_withholding_rate: Decimal = Decimal("0.0450")
    secondary_pension_nominals: list[Decimal] = Field(
        default_factory=list,
        description="Montos nominales de pasividades secundarias para consolidación",
    )


class PersonalServicesPayload(BaseModel):
    """Payload especializado de resultado para Servicios Personales (Fase 3A)."""

    vat_gross_billed: Decimal = Decimal("0.00")
    vat_tax_amount: Decimal = Decimal("0.00")
    vat_withholdings_suffered: Decimal = Decimal("0.00")
    vat_net_payable: Decimal = Decimal("0.00")

    irpf_gross_income: Decimal = Decimal("0.00")
    irpf_expense_deduction_amount: Decimal = Decimal("0.00")
    irpf_taxable_base: Decimal = Decimal("0.00")
    irpf_advance_amount: Decimal = Decimal("0.00")
    irpf_withholdings_suffered: Decimal = Decimal("0.00")
    irpf_net_advance_payable: Decimal = Decimal("0.00")

    cjppu_monthly_amount: Decimal = Decimal("0.00")
    bps_independent_amount: Decimal = Decimal("0.00")
    fonasa_advance_amount: Decimal = Decimal("0.00")


class LiteralEPayload(BaseModel):
    """Payload especializado de resultado para Pequeña Empresa - Literal E (Fase 3B)."""

    annual_gross_sales_uyu: Decimal = Decimal("0.00")
    annual_gross_sales_ui: Decimal = Decimal("0.00")
    threshold_ui: Decimal = Decimal("305000.00")
    ui_rate_used: Decimal = Decimal("0.0000")
    activity_months_age: int = 0
    dgi_discount_rate_applied: Decimal = Decimal("0.0000")
    dgi_monthly_fee: Decimal = Decimal("0.00")
    bps_patronal_monthly_fee: Decimal = Decimal("0.00")
    total_monthly_obligations: Decimal = Decimal("0.00")


class MonotributoPayload(BaseModel):
    """Payload de resultado para Monotributo Común y Social MIDES (Fase 3C)."""

    is_mides_regime: bool = False
    is_mides_certificate_valid: bool = False
    annual_gross_sales_uyu: Decimal = Decimal("0.00")
    annual_gross_sales_ui: Decimal = Decimal("0.00")
    threshold_ui: Decimal = Decimal("183000.00")
    ui_rate_used: Decimal = Decimal("0.0000")
    local_premises_sqm: Decimal | None = None
    employees_count: int = 0
    activity_months_age: int = 0
    mides_subsidy_rate_applied: Decimal = Decimal("0.0000")
    base_unipersonal_fee: Decimal = Decimal("0.00")
    final_monthly_monotributo_fee: Decimal = Decimal("0.00")


class IASSPayload(BaseModel):
    """Payload especializado de resultado para IASS y Pasividades (Fase 3D)."""

    gross_pension_amount: Decimal = Decimal("0.00")
    consolidated_gross_pension: Decimal = Decimal("0.00")
    iass_gross_tax: Decimal = Decimal("0.00")
    health_deduction_amount: Decimal = Decimal("0.00")
    iass_net_withholding: Decimal = Decimal("0.00")
    iass_marginal_rate: Decimal = Decimal("0.0000")
    fonasa_pension_withholding: Decimal = Decimal("0.00")
    total_withholdings: Decimal = Decimal("0.00")
    net_pension_liquid: Decimal = Decimal("0.00")
    is_multi_pension_consolidated: bool = False
