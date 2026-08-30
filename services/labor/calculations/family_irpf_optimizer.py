"""
Cálculo y optimización de IRPF: Liquidación Individual vs. Núcleo Familiar (DGI).
Deducciones por hijos y crédito fiscal por alquiler (8% Ley 18.083 / Ley 18.719).
Aritmética 100% determinística con Decimal.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from services.labor.domain.dtos import (
    FamilyIRPFOptimizerInput,
    FamilyIRPFOptimizerResult,
    IndividualIRPFSummary,
)
from services.labor.domain.tax_rules import (
    BPCValue,
    IRPFBracket,
    IRPFRuleSet,
)


def _compute_annual_gross_tax(
    annual_nominal: Decimal,
    brackets: list[IRPFBracket],
    bpc_val: Decimal,
) -> Decimal:
    """
    Calcula el IRPF anual bruto aplicando la escala progresiva.
    La base mensualizada se evalúa tramo a tramo y se anualiza multiplicando por 12.
    """
    if annual_nominal <= Decimal("0.00") or bpc_val <= Decimal("0.00"):
        return Decimal("0.00")

    monthly_nominal = (annual_nominal / Decimal("12")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    monthly_bpc = monthly_nominal / bpc_val
    monthly_gross_tax = Decimal("0.00")

    for bracket in brackets:
        if monthly_bpc > bracket.from_bpc:
            upper = bracket.to_bpc if bracket.to_bpc is not None else monthly_bpc
            taxable_bpc = min(monthly_bpc, upper) - bracket.from_bpc
            if taxable_bpc > Decimal("0.00"):
                taxable_uyu = (taxable_bpc * bpc_val).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                bracket_tax = (taxable_uyu * bracket.rate).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                monthly_gross_tax += bracket_tax

    annual_gross_tax = (monthly_gross_tax * Decimal("12")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return annual_gross_tax


def calculate_family_irpf_optimization(
    inp: FamilyIRPFOptimizerInput,
    rules: IRPFRuleSet,
    bpc: BPCValue,
) -> FamilyIRPFOptimizerResult:
    """
    Simula y compara la liquidación anual de IRPF individual vs. núcleo familiar.
    Retorna la recomendación óptima y el desglose de saldos ante DGI.
    """
    bpc_val = bpc.value
    notes: list[str] = []

    # ─────────────────────────────────────────────────────────────────────────
    # 1. CÁLCULO INDIVIDUAL (Persona 1 y Persona 2)
    # ─────────────────────────────────────────────────────────────────────────
    # Deducciones por hijos repartidas 50/50 en individual
    total_children_annual_bpc = (
        Decimal(inp.children_count) * rules.child_deduction_annual_bpc
        + Decimal(inp.disabled_children_count)
        * rules.disabled_child_deduction_annual_bpc
    )
    child_bpc_half = (total_children_annual_bpc / Decimal("2")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    child_deduction_uyu_half = (child_bpc_half * bpc_val).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # Crédito de alquiler 8% anual (Ley 18.083 / 18.719)
    total_rental_credit = Decimal("0.00")
    if inp.apply_rental_credit and inp.annual_rent_paid > Decimal("0.00"):
        total_rental_credit = (
            inp.annual_rent_paid * rules.rental_credit_rate
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    rental_credit_half = (total_rental_credit / Decimal("2")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # --- Miembro 1 ---
    gross_tax_1 = _compute_annual_gross_tax(
        inp.member1_annual_nominal, rules.brackets, bpc_val
    )
    deductions_base_1 = inp.member1_annual_social_security + child_deduction_uyu_half
    # Umbral 180 BPC anuales (15 BPC/mes)
    rate_1 = (
        rules.deduction_rate_low
        if inp.member1_annual_nominal
        <= (rules.deduction_threshold_bpc * Decimal("12") * bpc_val)
        else rules.deduction_rate_high
    )
    deductions_amount_1 = (deductions_base_1 * rate_1).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    tax_before_rent_1 = max(Decimal("0.00"), gross_tax_1 - deductions_amount_1)
    net_tax_1 = max(Decimal("0.00"), tax_before_rent_1 - rental_credit_half)
    balance_1 = (net_tax_1 - inp.member1_monthly_withholdings_paid).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    summary_1 = IndividualIRPFSummary(
        member_name=inp.member1_name,
        annual_nominal=inp.member1_annual_nominal,
        annual_social_security=inp.member1_annual_social_security,
        children_deduction_bpc=child_bpc_half,
        annual_gross_tax=gross_tax_1,
        annual_deductions_amount=deductions_amount_1,
        annual_net_tax=net_tax_1,
        monthly_withholdings_paid=inp.member1_monthly_withholdings_paid,
        rental_credit_applied=rental_credit_half,
        fiscal_balance=balance_1,
    )

    # --- Miembro 2 ---
    gross_tax_2 = _compute_annual_gross_tax(
        inp.member2_annual_nominal, rules.brackets, bpc_val
    )
    deductions_base_2 = inp.member2_annual_social_security + child_deduction_uyu_half
    rate_2 = (
        rules.deduction_rate_low
        if inp.member2_annual_nominal
        <= (rules.deduction_threshold_bpc * Decimal("12") * bpc_val)
        else rules.deduction_rate_high
    )
    deductions_amount_2 = (deductions_base_2 * rate_2).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    tax_before_rent_2 = max(Decimal("0.00"), gross_tax_2 - deductions_amount_2)
    net_tax_2 = max(Decimal("0.00"), tax_before_rent_2 - rental_credit_half)
    balance_2 = (net_tax_2 - inp.member2_monthly_withholdings_paid).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    summary_2 = IndividualIRPFSummary(
        member_name=inp.member2_name,
        annual_nominal=inp.member2_annual_nominal,
        annual_social_security=inp.member2_annual_social_security,
        children_deduction_bpc=child_bpc_half,
        annual_gross_tax=gross_tax_2,
        annual_deductions_amount=deductions_amount_2,
        annual_net_tax=net_tax_2,
        monthly_withholdings_paid=inp.member2_monthly_withholdings_paid,
        rental_credit_applied=rental_credit_half,
        fiscal_balance=balance_2,
    )

    total_indiv_net_tax = net_tax_1 + net_tax_2
    total_indiv_withholdings = (
        inp.member1_monthly_withholdings_paid + inp.member2_monthly_withholdings_paid
    )
    total_indiv_balance = balance_1 + balance_2

    # ─────────────────────────────────────────────────────────────────────────
    # 2. CÁLCULO NÚCLEO FAMILIAR (Matrimonio / Concubinato)
    # ─────────────────────────────────────────────────────────────────────────
    family_gross = inp.member1_annual_nominal + inp.member2_annual_nominal

    # Determinar si ambos generan rentas relevantes (> 12 BPC anuales / 1 BPC mes)
    m1_has_income = inp.member1_annual_nominal >= (Decimal("12.0") * bpc_val)
    m2_has_income = inp.member2_annual_nominal >= (Decimal("12.0") * bpc_val)

    if m1_has_income and m2_has_income:
        variant = "ambos_generan"
        family_brackets = rules.family_unit_brackets_both_generate
        notes.append(
            "Núcleo Familiar: Escala A (ambos generan rentas). "
            "MNI: 14 BPC/mes (168 BPC/año)."
        )
    else:
        variant = "unico_generador"
        family_brackets = rules.family_unit_brackets_single_generates
        notes.append(
            "Núcleo Familiar: Escala B (un solo generador). "
            "MNI: 8 BPC/mes (96 BPC/año)."
        )

    family_gross_tax = _compute_annual_gross_tax(family_gross, family_brackets, bpc_val)

    # Deducciones conjuntas
    total_children_uyu = (total_children_annual_bpc * bpc_val).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    family_deductions_base = (
        inp.member1_annual_social_security
        + inp.member2_annual_social_security
        + total_children_uyu
    )

    # Tasa de deducción en núcleo familiar: umbral de 15 BPC por integrante generador
    threshold_multiplier = (
        Decimal("24.0") if variant == "ambos_generan" else Decimal("12.0")
    )
    family_rate = (
        rules.deduction_rate_low
        if family_gross
        <= (rules.deduction_threshold_bpc * threshold_multiplier * bpc_val)
        else rules.deduction_rate_high
    )
    family_deductions_amount = (family_deductions_base * family_rate).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    family_tax_before_credits = max(
        Decimal("0.00"), family_gross_tax - family_deductions_amount
    )

    # Deducción de crédito hipotecario (Ley 18.910 - tope 36 BPC)
    mortgage_deduction = Decimal("0.00")
    if inp.apply_mortgage_deduction and inp.annual_mortgage_payments > Decimal("0.00"):
        max_mortgage_bpc_uyu = rules.mortgage_deduction_max_annual_bpc * bpc_val
        computable_mortgage = min(inp.annual_mortgage_payments, max_mortgage_bpc_uyu)
        mortgage_deduction = (computable_mortgage * family_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    family_net_tax = max(
        Decimal("0.00"),
        family_tax_before_credits - total_rental_credit - mortgage_deduction,
    )
    family_balance = (family_net_tax - total_indiv_withholdings).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 3. VEREDICTO Y RECOMENDACIÓN
    # ─────────────────────────────────────────────────────────────────────────
    tax_diff = (total_indiv_net_tax - family_net_tax).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    if tax_diff > Decimal("1.00"):
        recommended = "NUCLEO_FAMILIAR"
        savings = tax_diff
        recommendation_txt = (
            f"¡Conviene declarar como NÚCLEO FAMILIAR! "
            f"Ahorro anual estimado: $ {savings:,.2f} UYU."
        ).replace(",", ".")
    elif tax_diff < Decimal("-1.00"):
        recommended = "INDIVIDUAL"
        savings = abs(tax_diff)
        recommendation_txt = (
            f"Conviene mantener LIQUIDACIÓN INDIVIDUAL. "
            f"Sobrecosto en núcleo familiar: $ {savings:,.2f} UYU."
        ).replace(",", ".")
    else:
        recommended = "INDIFERENTE"
        savings = Decimal("0.00")
        recommendation_txt = (
            "El resultado tributario es equivalente en ambas modalidades."
        )

    if total_rental_credit > Decimal("0.00"):
        rent_txt = f"{inp.annual_rent_paid:,.0f}"
        cred_txt = f"{total_rental_credit:,.2f}"
        notes.append(
            f"Crédito por alquiler (8% de $ {rent_txt}): "
            f"$ {cred_txt} UYU (Ley 18.083 / Ley 18.719 Art. 764).".replace(",", ".")
        )

    return FamilyIRPFOptimizerResult(
        year=inp.year,
        bpc_value=bpc_val,
        member1_summary=summary_1,
        member2_summary=summary_2,
        total_individual_net_tax=total_indiv_net_tax,
        total_individual_withholdings=total_indiv_withholdings,
        total_individual_balance=total_indiv_balance,
        family_gross_income=family_gross,
        family_unit_variant=variant,
        family_gross_tax=family_gross_tax,
        family_deductions_base=family_deductions_base,
        family_deduction_rate=family_rate,
        family_deductions_amount=family_deductions_amount,
        family_tax_before_credits=family_tax_before_credits,
        rental_credit_amount=total_rental_credit,
        mortgage_deduction_amount=mortgage_deduction,
        family_net_tax=family_net_tax,
        total_family_withholdings=total_indiv_withholdings,
        family_balance=family_balance,
        tax_difference=tax_diff,
        recommended_option=recommended,
        annual_savings=savings,
        recommendation_summary=recommendation_txt,
        legal_notes=notes,
    )
