"""
Cálculo de IASS y Retenciones sobre Pasividades (Ley 18.314 / Ley 20.124).
Aritmética determinística 100% Decimal (cero float).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from services.labor.domain.dtos import IASSPayload, PensionProfile
from services.labor.domain.enums import CalculationStatus
from services.labor.domain.models import CalculationResult
from services.labor.domain.tax_rules import BPCValue, IASSRuleSet


def calculate_pension_settlement(
    profile: PensionProfile,
    rules: IASSRuleSet | None,
    bpc: BPCValue | None,
) -> CalculationResult:
    """
    Liquida el IASS mensual con escala progresiva y deducciones de salud para pasivos.
    """
    review_reasons: list[str] = []
    legal_refs: list[str] = []
    notes: list[str] = []

    if rules is None or bpc is None:
        return CalculationResult(
            rule_version="UY-BPS-IASS-2026-v1",
            status=CalculationStatus.REQUIRES_REVIEW,
            pension_profile=profile,
            review_reasons=["Reglas de IASS o BPC no disponibles para el año."],
        )

    legal_refs.append(rules.source)
    legal_refs.append(bpc.source_decree)

    primary_nominal = profile.monthly_pension_nominal
    secondary_nominals = profile.secondary_pension_nominals
    is_consolidated = len(secondary_nominals) > 0

    consolidated_gross = primary_nominal + sum(secondary_nominals)
    total_pension_bpc = (consolidated_gross / bpc.value).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )

    # 1. Escala Progresiva de IASS (5 Tramos oficiales - Ley 20.124)
    gross_tax_consolidated = Decimal("0.00")
    marginal_rate = Decimal("0.0000")

    for bracket in rules.brackets:
        if total_pension_bpc > bracket.from_bpc:
            if bracket.to_bpc is not None:
                taxable_in_tier_bpc = (
                    min(total_pension_bpc, bracket.to_bpc) - bracket.from_bpc
                )
            else:
                taxable_in_tier_bpc = total_pension_bpc - bracket.from_bpc

            tier_tax = (taxable_in_tier_bpc * bpc.value * bracket.rate).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            gross_tax_consolidated += tier_tax

            if bracket.rate > Decimal("0.0000"):
                marginal_rate = bracket.rate

    # 2. Deducciones de Salud (Cuota mutual / FONASA pasivos - Ley 20.124)
    if total_pension_bpc <= rules.deduction_threshold_bpc:
        deduction_rate = rules.deduction_rate_low
    else:
        deduction_rate = rules.deduction_rate_high

    health_deduction = (
        rules.standard_health_deduction_monthly_bpc * bpc.value * deduction_rate
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    net_iass_consolidated = max(
        Decimal("0.00"), gross_tax_consolidated - health_deduction
    )

    # Si hay consolidación de múltiples pasividades, prorratear al ingreso principal
    if is_consolidated and consolidated_gross > Decimal("0.00"):
        share = primary_nominal / consolidated_gross
        iass_withholding = (net_iass_consolidated * share).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        notes.append(
            f"Multicaixa: Total=${consolidated_gross} ({total_pension_bpc} BPC). "
            f"IASS=${net_iass_consolidated}, Ret. prop=${iass_withholding}."
        )
    else:
        iass_withholding = net_iass_consolidated

    # 3. Retención FONASA para Pasivos (Ley 18.731)
    fonasa_withholding = Decimal("0.00")
    if profile.has_fonasa_coverage and primary_nominal > Decimal("0.00"):
        fonasa_withholding = (
            primary_nominal * profile.fonasa_withholding_rate
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        pct_fonasa = profile.fonasa_withholding_rate * Decimal("100")
        notes.append(f"FONASA pasivo ({pct_fonasa}%): ${fonasa_withholding} UYU.")

    total_withholdings = iass_withholding + fonasa_withholding
    net_liquid = primary_nominal - total_withholdings

    notes.append(
        f"IASS: Bruto=${gross_tax_consolidated}, Deducción salud=${health_deduction}, "
        f"IASS neto=${iass_withholding}, Líquido=${net_liquid}."
    )

    payload = IASSPayload(
        gross_pension_amount=primary_nominal,
        consolidated_gross_pension=consolidated_gross,
        iass_gross_tax=gross_tax_consolidated,
        health_deduction_amount=health_deduction,
        iass_net_withholding=iass_withholding,
        iass_marginal_rate=marginal_rate,
        fonasa_pension_withholding=fonasa_withholding,
        total_withholdings=total_withholdings,
        net_pension_liquid=net_liquid,
        is_multi_pension_consolidated=is_consolidated,
    )

    return CalculationResult(
        rule_version=rules.rule_version,
        status=CalculationStatus.CALCULATED,
        currency="UYU",
        total_computable=primary_nominal,
        nominal_amount=primary_nominal,
        fonasa_amount=fonasa_withholding,
        irpf_gross_tax=gross_tax_consolidated,
        irpf_deductions_amount=health_deduction,
        irpf_net_withholding=iass_withholding,
        irpf_marginal_rate=marginal_rate,
        total_withholdings=total_withholdings,
        final_amount=net_liquid,
        liquid_amount=net_liquid,
        iass_payload=payload,
        pension_profile=profile,
        review_reasons=review_reasons,
        legal_references=legal_refs,
        explanation_notes=notes,
        calculated_at_utc=datetime.now(UTC),
    )
