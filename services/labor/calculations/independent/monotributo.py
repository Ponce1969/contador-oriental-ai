"""
Cálculo y evaluación para Monotributo Común y Social MIDES (BPS / DGI).
(Ley 18.083 Arts. 70-82 / Dec. 199/007 / Ley 18.874 / Dec. 220/012).
Aritmética determinística 100% Decimal.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal

from services.labor.calculations.independent.literal_e import (
    calculate_activity_months,
)
from services.labor.domain.dtos import (
    EligibilityEvaluation,
    IndependentProfile,
    MonotributoPayload,
)
from services.labor.domain.enums import (
    CalculationStatus,
    EligibilityStatus,
    IndependentTaxRegime,
)
from services.labor.domain.models import CalculationResult
from services.labor.domain.tax_rules import MonotributoRuleSet, UIValue


def calculate_monotributo_settlement(
    annual_gross_sales_uyu: Decimal,
    profile: IndependentProfile,
    rules: MonotributoRuleSet | None,
    ui_value: UIValue | None,
    calculation_date: date | None = None,
) -> CalculationResult:
    """
    Evalúa elegibilidad comercial y liquida la cuota única mensual unificada BPS+DGI.
    """
    violations: list[str] = []
    review_reasons: list[str] = []
    legal_refs: list[str] = []
    notes: list[str] = []

    today = calculation_date or date.today()
    is_mides = profile.regime == IndependentTaxRegime.MONOTRIBUTO_MIDES

    if profile.regime not in {
        IndependentTaxRegime.MONOTRIBUTO,
        IndependentTaxRegime.MONOTRIBUTO_MIDES,
    }:
        violations.append(
            f"El régimen '{profile.regime}' no corresponde a Monotributo."
        )

    if rules is None:
        return CalculationResult(
            rule_version="UY-BPS-MONO-2026-v1",
            status=CalculationStatus.REQUIRES_REVIEW,
            independent_profile=profile,
            review_reasons=["Reglas de Monotributo no disponibles para el año."],
        )

    if ui_value is None:
        return CalculationResult(
            rule_version=rules.rule_version,
            status=CalculationStatus.REQUIRES_REVIEW,
            independent_profile=profile,
            review_reasons=["Cotización oficial de la UI no disponible."],
        )

    legal_refs.append(rules.source)

    # 1. Evaluación de Elegibilidad Física (Superficie del local <= 15 m2)
    if profile.local_premises_sqm is not None:
        if profile.local_premises_sqm > rules.max_premises_sqm:
            violations.append(
                f"Local ({profile.local_premises_sqm} m2) "
                f"supera límite {rules.max_premises_sqm} m2."
            )

    # 2. Evaluación de Dependientes (Máximo 1 dependiente)
    if profile.employees_count > rules.max_employees_unipersonal:
        violations.append(
            f"Personal ({profile.employees_count}) "
            f"supera límite de {rules.max_employees_unipersonal} dependiente."
        )

    # 3. Evaluación de Ventas en UI
    sales_in_ui = (annual_gross_sales_uyu / ui_value.value).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    is_sociedad = profile.partner_count is not None and profile.partner_count > 1
    threshold_ui = (
        rules.threshold_sociedad_ui if is_sociedad else rules.threshold_unipersonal_ui
    )

    if sales_in_ui > threshold_ui:
        violations.append(
            f"Ventas ${annual_gross_sales_uyu} ({sales_in_ui} UI) "
            f"superan tope {threshold_ui} UI."
        )

    # 4. Evaluación de Certificado MIDES
    is_mides_valid = False
    if is_mides:
        if profile.has_mides_certificate:
            if (
                profile.mides_certificate_expiry is None
                or profile.mides_certificate_expiry >= today
            ):
                is_mides_valid = True
            else:
                review_reasons.append(
                    "Certificado MIDES vencido; liquida al 100% como Monotributo Común."
                )
        else:
            review_reasons.append(
                "Sin certificado MIDES avalado; liquida como Monotributo Común."
            )

    # 5. Cómputo de la Cuota Unificada
    base_fee = (
        rules.base_fee_sociedad_monthly
        if is_sociedad
        else rules.base_fee_unipersonal_monthly
    )

    months_age = 1
    if profile.regime_start_date is not None:
        months_age = calculate_activity_months(profile.regime_start_date, today)

    subsidy_rate = Decimal("1.0000")
    if is_mides and is_mides_valid:
        if months_age <= rules.mides_tier_1_months:
            subsidy_rate = rules.mides_tier_1_rate
            mides_label = "Año 1 MIDES (25%)"
        elif months_age <= rules.mides_tier_2_months:
            subsidy_rate = rules.mides_tier_2_rate
            mides_label = "Año 2 MIDES (50%)"
        elif months_age <= rules.mides_tier_3_months:
            subsidy_rate = rules.mides_tier_3_rate
            mides_label = "Año 3 MIDES (75%)"
        else:
            subsidy_rate = rules.mides_tier_4_rate
            mides_label = "Año 4+ MIDES (100%)"
    else:
        mides_label = "Cuota Plena (100%)"

    final_fee = (base_fee * subsidy_rate).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    notes.append(
        f"Monotributo: Ventas ${annual_gross_sales_uyu} ({sales_in_ui} UI). "
        f"Antigüedad {months_age} m ({mides_label}). "
        f"Cuota=${final_fee} UYU."
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

    payload = MonotributoPayload(
        is_mides_regime=is_mides,
        is_mides_certificate_valid=is_mides_valid,
        annual_gross_sales_uyu=annual_gross_sales_uyu,
        annual_gross_sales_ui=sales_in_ui,
        threshold_ui=threshold_ui,
        ui_rate_used=ui_value.value,
        local_premises_sqm=profile.local_premises_sqm,
        employees_count=profile.employees_count,
        activity_months_age=months_age,
        mides_subsidy_rate_applied=subsidy_rate,
        base_unipersonal_fee=base_fee,
        final_monthly_monotributo_fee=final_fee,
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
        final_amount=final_fee,
        liquid_amount=final_fee,
        total_withholdings=final_fee,
        eligibility=eligibility,
        monotributo_payload=payload,
        independent_profile=profile,
        review_reasons=review_reasons,
        legal_references=legal_refs,
        explanation_notes=notes,
        calculated_at_utc=datetime.now(UTC),
    )
