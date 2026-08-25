"""
Orquestador de liquidación para Servicios Personales (Fase 3A).
Integra evaluación de elegibilidad, IVA, IRPF y CJPPU.
Aritmética determinística 100% Decimal.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from services.labor.calculations.independent.cjppu_calculator import (
    calculate_cjppu_contribution,
)
from services.labor.calculations.independent.eligibility import (
    PersonalServicesEligibilityEvaluator,
)
from services.labor.calculations.independent.irpf_independent import (
    calculate_bimonthly_irpf_advance,
)
from services.labor.calculations.independent.iva_calculator import (
    calculate_personal_services_vat,
)
from services.labor.domain.dtos import (
    EligibilityEvaluation,
    IndependentProfile,
    PersonalServicesPayload,
)
from services.labor.domain.enums import (
    CalculationStatus,
    EligibilityStatus,
    PensionFundType,
)
from services.labor.domain.models import CalculationResult
from services.labor.domain.tax_rules import (
    CJPPURuleSet,
    IRPFIndependentRuleSet,
    IVARuleSet,
)


def calculate_personal_services_settlement(
    net_billed_amount: Decimal,
    profile: IndependentProfile,
    iva_rules: IVARuleSet | None,
    irpf_rules: IRPFIndependentRuleSet | None,
    cjppu_rules: CJPPURuleSet | None,
    is_client_cede: bool = False,
    vat_rate_type: str = "BASIC",
    actual_documented_expenses: Decimal | None = None,
    irpf_withholdings_suffered: Decimal = Decimal("0.00"),
) -> CalculationResult:
    """
    Orquesta la liquidación de tributos para Servicios Personales.
    """
    review_reasons: list[str] = []
    legal_refs: list[str] = []
    notes: list[str] = []

    # 1. Evaluación de Elegibilidad
    eval_res: EligibilityEvaluation = PersonalServicesEligibilityEvaluator.evaluate(
        profile
    )
    if not eval_res.can_proceed_to_calculation:
        return CalculationResult(
            rule_version="UY-INDEPENDENT-SERV-2026-v1",
            status=CalculationStatus.INSUFFICIENT_DATA,
            eligibility=eval_res,
            independent_profile=profile,
            missing_information=eval_res.violations,
            review_reasons=eval_res.review_reasons,
        )

    if iva_rules is None or irpf_rules is None:
        return CalculationResult(
            rule_version="UY-INDEPENDENT-SERV-2026-v1",
            status=CalculationStatus.REQUIRES_REVIEW,
            eligibility=eval_res,
            independent_profile=profile,
            review_reasons=["Reglas de IVA o IRPF no disponibles para el período."],
        )

    legal_refs.append(iva_rules.source)
    legal_refs.append(irpf_rules.source)

    # 2. Cómputo de IVA
    vat_res = calculate_personal_services_vat(
        net_billed_amount=net_billed_amount,
        rules=iva_rules,
        rate_type=vat_rate_type,
        is_client_cede=is_client_cede,
    )
    notes.extend(vat_res.notes)

    # 3. Cómputo de Anticipo de IRPF
    irpf_res = calculate_bimonthly_irpf_advance(
        bimonthly_billed_without_vat=net_billed_amount,
        rules=irpf_rules,
        withholdings_suffered=irpf_withholdings_suffered,
        actual_documented_expenses=actual_documented_expenses,
    )
    notes.extend(irpf_res.notes)

    # 4. Cómputo de Previsión Social (CJPPU si aplica)
    cjppu_amount = Decimal("0.00")
    if profile.pension_fund == PensionFundType.CJPPU and profile.cjppu_category:
        if cjppu_rules is None:
            review_reasons.append("Reglas de CJPPU no disponibles para el año fiscal.")
        else:
            legal_refs.append(cjppu_rules.source)
            cjppu_calc = calculate_cjppu_contribution(
                category=profile.cjppu_category, rules=cjppu_rules
            )
            cjppu_amount = cjppu_calc.monthly_contribution_amount
            notes.extend(cjppu_calc.notes)

    # 5. Payload de Resultados Especializado
    payload = PersonalServicesPayload(
        vat_gross_billed=net_billed_amount + vat_res.vat_gross_amount,
        vat_tax_amount=vat_res.vat_gross_amount,
        vat_withholdings_suffered=vat_res.withholding_cede_amount,
        vat_net_payable=vat_res.vat_net_payable,
        irpf_gross_income=net_billed_amount,
        irpf_expense_deduction_amount=irpf_res.expense_deduction_amount,
        irpf_taxable_base=irpf_res.taxable_base,
        irpf_advance_amount=irpf_res.gross_advance_amount,
        irpf_withholdings_suffered=irpf_res.withholdings_suffered,
        irpf_net_advance_payable=irpf_res.net_advance_payable,
        cjppu_monthly_amount=cjppu_amount,
    )

    total_taxes = vat_res.vat_net_payable + irpf_res.net_advance_payable
    total_ss = cjppu_amount
    net_after_taxes = (
        net_billed_amount + vat_res.vat_gross_amount - total_taxes - total_ss
    )

    if eval_res.status == EligibilityStatus.REQUIRES_REVIEW:
        review_reasons.extend(eval_res.review_reasons)

    status = (
        CalculationStatus.REQUIRES_REVIEW
        if review_reasons
        else CalculationStatus.CALCULATED
    )

    return CalculationResult(
        rule_version=f"{iva_rules.rule_version}+{irpf_rules.rule_version}",
        status=status,
        currency="UYU",
        total_computable=net_billed_amount,
        final_amount=net_after_taxes,
        liquid_amount=net_after_taxes,
        total_withholdings=total_taxes + total_ss,
        eligibility=eval_res,
        personal_services_payload=payload,
        independent_profile=profile,
        review_reasons=review_reasons,
        legal_references=legal_refs,
        explanation_notes=notes,
        calculated_at_utc=datetime.now(UTC),
    )
