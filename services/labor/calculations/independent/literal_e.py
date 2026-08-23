"""
Cálculo y evaluación para Pequeña Empresa - Régimen Literal E (DGI / BPS).
(Título 4 T.O. 1996 Art. 52 Lit. E / Ley 18.083 / Ley 19.996 Art. 287).
Aritmética determinística 100% Decimal.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal

from services.labor.domain.dtos import (
    EligibilityEvaluation,
    IndependentProfile,
    LiteralEPayload,
)
from services.labor.domain.enums import (
    CalculationStatus,
    EligibilityStatus,
    IndependentTaxRegime,
)
from services.labor.domain.models import CalculationResult
from services.labor.domain.tax_rules import LiteralERuleSet, UIValue


def calculate_activity_months(start_date: date, current_date: date) -> int:
    """Calcula la cantidad de meses transcurridos desde el inicio de actividades."""
    if current_date < start_date:
        return 0
    years_diff = current_date.year - start_date.year
    months_diff = current_date.month - start_date.month
    total_months = (years_diff * 12) + months_diff
    return max(1, total_months + 1)


def calculate_literal_e_settlement(
    annual_gross_sales_uyu: Decimal,
    profile: IndependentProfile,
    rules: LiteralERuleSet | None,
    ui_value: UIValue | None,
    calculation_date: date | None = None,
) -> CalculationResult:
    """
    Evalúa elegibilidad (tope 305.000 UI) y liquida cuotas DGI y BPS.
    """
    violations: list[str] = []
    review_reasons: list[str] = []
    legal_refs: list[str] = []
    notes: list[str] = []

    today = calculation_date or date.today()

    if profile.regime != IndependentTaxRegime.LITERAL_E:
        violations.append(f"El régimen declarado '{profile.regime}' no es Literal E.")

    if rules is None:
        return CalculationResult(
            rule_version="UY-DGI-LIT-E-2026-v1",
            status=CalculationStatus.REQUIRES_REVIEW,
            independent_profile=profile,
            review_reasons=["Reglas de Literal E no disponibles para el año."],
        )

    if ui_value is None:
        return CalculationResult(
            rule_version=rules.rule_version,
            status=CalculationStatus.REQUIRES_REVIEW,
            independent_profile=profile,
            review_reasons=["Cotización oficial de la UI no disponible."],
        )

    legal_refs.append(rules.source)

    # 1. Evaluación del Tope de Inclusión en Unidades Indexadas (305.000 UI)
    sales_in_ui = (annual_gross_sales_uyu / ui_value.value).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    is_under_threshold = sales_in_ui <= rules.threshold_ui
    if not is_under_threshold:
        violations.append(
            f"Ventas de ${annual_gross_sales_uyu} UYU ({sales_in_ui} UI) "
            f"superan tope {rules.threshold_ui} UI. Debe pasar a IRAE/IVA."
        )
        review_reasons.append("Exclusión preceptiva de Literal E por exceso de ventas.")

    # 2. Determinación de Antigüedad y Escalonamiento de Cuota DGI (Ley 19.996)
    if profile.regime_start_date is not None:
        months_age = calculate_activity_months(profile.regime_start_date, today)
    else:
        months_age = 1
        review_reasons.append("Sin fecha de inicio; se asume Año 1 (25%) provisorio.")

    if months_age <= rules.tier_1_months:
        discount_rate = rules.tier_1_rate
        tier_label = "Año 1 (25%)"
    elif months_age <= rules.tier_2_months:
        discount_rate = rules.tier_2_rate
        tier_label = "Año 2 (50%)"
    else:
        discount_rate = rules.tier_3_rate
        tier_label = "Año 3+ (100% Plena)"

    # 3. Cómputo de Cuotas Mensuales Fijas
    dgi_fee = (rules.dgi_base_fee_monthly * discount_rate).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    bps_fee = rules.bps_patronal_fee_monthly

    total_monthly = dgi_fee + bps_fee

    notes.append(
        f"Literal E: Ventas ${annual_gross_sales_uyu} ({sales_in_ui} UI). "
        f"Antigüedad {months_age} meses ({tier_label}). "
        f"DGI=${dgi_fee}, BPS=${bps_fee}. Total=${total_monthly}."
    )

    is_eligible = len(violations) == 0
    eval_status = (
        EligibilityStatus.ELIGIBLE if is_eligible else EligibilityStatus.INELIGIBLE
    )
    if is_eligible and review_reasons:
        eval_status = EligibilityStatus.REQUIRES_REVIEW

    eligibility = EligibilityEvaluation(
        status=eval_status,
        violations=violations,
        review_reasons=review_reasons,
        can_proceed_to_calculation=is_eligible,
    )

    payload = LiteralEPayload(
        annual_gross_sales_uyu=annual_gross_sales_uyu,
        annual_gross_sales_ui=sales_in_ui,
        threshold_ui=rules.threshold_ui,
        ui_rate_used=ui_value.value,
        activity_months_age=months_age,
        dgi_discount_rate_applied=discount_rate,
        dgi_monthly_fee=dgi_fee,
        bps_patronal_monthly_fee=bps_fee,
        total_monthly_obligations=total_monthly,
    )

    calc_status = (
        CalculationStatus.CALCULATED
        if is_eligible and not review_reasons
        else (
            CalculationStatus.REQUIRES_REVIEW
            if is_eligible
            else CalculationStatus.INSUFFICIENT_DATA
        )
    )

    return CalculationResult(
        rule_version=rules.rule_version,
        status=calc_status,
        currency="UYU",
        total_computable=annual_gross_sales_uyu,
        final_amount=total_monthly,
        liquid_amount=total_monthly,
        total_withholdings=total_monthly,
        eligibility=eligibility,
        literal_e_payload=payload,
        independent_profile=profile,
        review_reasons=review_reasons,
        legal_references=legal_refs,
        explanation_notes=notes,
        calculated_at_utc=datetime.now(UTC),
    )
