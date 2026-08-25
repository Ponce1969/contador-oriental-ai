"""
Orquestador del submotor de retenciones laborales uruguayas.
Coordina Seguridad Social, FONASA e IRPF, y provee estimación inversa.
Aritmética determinística 100% Decimal (cero float).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from services.labor.calculations.fonasa import calculate_fonasa
from services.labor.calculations.irpf import calculate_monthly_irpf_withholding
from services.labor.calculations.social_security import calculate_social_security
from services.labor.domain.enums import (
    CalculationStatus,
    EstimationAccuracy,
    RuleVerificationStatus,
)
from services.labor.domain.models import (
    CalculationResult,
    NominalEstimationResult,
    TaxProfile,
)
from services.labor.domain.tax_rules import (
    BPCValue,
    IRPFRuleSet,
    SocialSecurityRuleSet,
)


def calculate_monthly_withholdings(
    nominal: Decimal,
    profile: TaxProfile,
    ss_rules: SocialSecurityRuleSet | None,
    irpf_rules: IRPFRuleSet | None,
    bpc: BPCValue | None,
) -> CalculationResult:
    """
    Orquesta la simulación del recibo de sueldo mensual dependiente en Uruguay.
    Calcula Montepío (15%), FRL (0.10%), FONASA (3-8%) e IRPF Categoría II.
    """
    review_reasons: list[str] = []
    legal_refs: list[str] = []

    # 1. Guardas de validación e información faltante
    if nominal <= Decimal("0.00"):
        return CalculationResult(
            rule_version="UY-WITHHOLDING-2026-v1",
            status=CalculationStatus.INSUFFICIENT_DATA,
            missing_fields=["nominal_amount"],
            missing_information=[
                "El salario nominal debe ser un monto positivo en Decimal."
            ],
        )

    if bpc is None or bpc.verification_status != RuleVerificationStatus.VERIFIED:
        return CalculationResult(
            rule_version="UY-WITHHOLDING-2026-v1",
            status=CalculationStatus.REQUIRES_REVIEW,
            review_reasons=[
                "No existe una BPC oficial verificada para el año del cálculo."
            ],
            missing_information=["BPCValue verificada"],
        )

    if ss_rules is None or irpf_rules is None:
        return CalculationResult(
            rule_version="UY-WITHHOLDING-2026-v1",
            status=CalculationStatus.REQUIRES_REVIEW,
            review_reasons=[
                "Reglas de Seguridad Social o IRPF no disponibles para el período."
            ],
            missing_information=["SocialSecurityRuleSet / IRPFRuleSet"],
        )

    # 2. Cómputo de Seguridad Social (Montepío + FRL)
    ss_res = calculate_social_security(nominal, ss_rules)
    legal_refs.append(ss_rules.source)
    if ss_res.exceeds_cap:
        review_reasons.extend(ss_res.notes)

    # 3. Cómputo de FONASA
    fonasa_res = calculate_fonasa(nominal, profile, ss_rules, bpc)
    legal_refs.append("Ley 18.211 (Seguro Nacional de Salud)")

    # Total aportes a la seguridad social
    total_ss = ss_res.total_amount + fonasa_res.fonasa_amount

    # 4. Cómputo de IRPF Retención Mensual
    irpf_res = calculate_monthly_irpf_withholding(
        nominal=nominal,
        social_security_contributions=total_ss,
        profile=profile,
        rules=irpf_rules,
        bpc=bpc,
    )
    legal_refs.append(irpf_rules.source)

    # 5. Totales y Líquido
    total_withholdings = total_ss + irpf_res.net_withholding
    liquid_amount = nominal - total_withholdings

    status = (
        CalculationStatus.REQUIRES_REVIEW
        if review_reasons
        else CalculationStatus.CALCULATED
    )

    all_notes = ss_res.notes + fonasa_res.notes + irpf_res.notes

    return CalculationResult(
        rule_version=f"{ss_rules.rule_version}+{irpf_rules.rule_version}",
        status=status,
        currency="UYU",
        nominal_amount=nominal,
        montepio_amount=ss_res.montepio_amount,
        frl_amount=ss_res.frl_amount,
        fonasa_amount=fonasa_res.fonasa_amount,
        fonasa_effective_rate=fonasa_res.effective_rate,
        total_social_security=total_ss,
        irpf_gross_tax=irpf_res.gross_tax,
        irpf_deductions_amount=irpf_res.deductions_amount,
        irpf_net_withholding=irpf_res.net_withholding,
        irpf_marginal_rate=irpf_res.marginal_rate,
        total_withholdings=total_withholdings,
        liquid_amount=liquid_amount,
        final_amount=liquid_amount,
        review_reasons=review_reasons,
        legal_references=legal_refs,
        explanation_notes=all_notes,
        calculated_at_utc=datetime.now(UTC),
    )


def estimate_nominal_from_liquid(
    liquid: Decimal,
    profile: TaxProfile,
    ss_rules: SocialSecurityRuleSet | None,
    irpf_rules: IRPFRuleSet | None,
    bpc: BPCValue | None,
    tolerance: Decimal = Decimal("0.01"),
    max_iterations: int = 50,
) -> NominalEstimationResult:
    """
    Resuelve determinísticamente el salario nominal correspondiente a un líquido dado
    mediante búsqueda binaria por bisección en Decimal.
    """
    if liquid <= Decimal("0.00"):
        empty_res = CalculationResult(
            rule_version="UY-INVERSE-2026-v1",
            status=CalculationStatus.INSUFFICIENT_DATA,
            missing_fields=["target_liquid_amount"],
        )
        return NominalEstimationResult(
            status=EstimationAccuracy.REQUIRES_REVIEW,
            requested_liquid=liquid,
            estimated_nominal=Decimal("0.00"),
            resulting_liquid=Decimal("0.00"),
            difference=liquid,
            tolerance=tolerance,
            iterations_used=0,
            withholdings_breakdown=empty_res,
        )

    # Rango de búsqueda: entre el líquido y hasta 3x el líquido
    low = liquid
    high = liquid * Decimal("3.0")
    iterations = 0
    best_nominal = low

    for i in range(1, max_iterations + 1):
        iterations = i
        mid = ((low + high) / Decimal("2")).quantize(Decimal("0.01"))
        best_nominal = mid

        calc = calculate_monthly_withholdings(mid, profile, ss_rules, irpf_rules, bpc)
        if calc.status == CalculationStatus.REQUIRES_REVIEW:
            return NominalEstimationResult(
                status=EstimationAccuracy.REQUIRES_REVIEW,
                requested_liquid=liquid,
                estimated_nominal=mid,
                resulting_liquid=calc.liquid_amount,
                difference=abs(calc.liquid_amount - liquid),
                tolerance=tolerance,
                iterations_used=iterations,
                withholdings_breakdown=calc,
            )

        diff = calc.liquid_amount - liquid
        if abs(diff) <= tolerance:
            break
        elif diff < Decimal("0.00"):
            low = mid
        else:
            high = mid

    # Verificación estricta del resultado
    final_calc = calculate_monthly_withholdings(
        best_nominal, profile, ss_rules, irpf_rules, bpc
    )
    final_diff = abs(final_calc.liquid_amount - liquid)

    if final_diff == Decimal("0.00"):
        status = EstimationAccuracy.EXACT
    elif final_diff <= tolerance:
        status = EstimationAccuracy.WITHIN_TOLERANCE
    else:
        status = EstimationAccuracy.REQUIRES_REVIEW

    return NominalEstimationResult(
        status=status,
        requested_liquid=liquid,
        estimated_nominal=best_nominal,
        resulting_liquid=final_calc.liquid_amount,
        difference=final_diff,
        tolerance=tolerance,
        iterations_used=iterations,
        withholdings_breakdown=final_calc,
    )
