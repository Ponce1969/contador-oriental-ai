"""
Cálculo de IRPF Categoría II (Rentas de Trabajo Dependiente).
Ley 18.083 / Dec. 148/007 / Ley 20.124.
Aritmética determinística 100% Decimal.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel

from services.labor.domain.models import TaxProfile
from services.labor.domain.tax_rules import BPCValue, IRPFRuleSet


class IRPFWithholdingResult(BaseModel):
    """Resultado de la simulación de retención mensual de IRPF."""

    taxable_base_monthly: Decimal
    taxable_base_with_ficto: Decimal
    gross_tax: Decimal
    deductions_base: Decimal
    deduction_rate: Decimal
    deductions_amount: Decimal
    net_withholding: Decimal
    marginal_rate: Decimal
    notes: list[str] = []


class IRPFAnnualSettlementResult(BaseModel):
    """Resultado de la liquidación y ajuste anual de IRPF."""

    annual_gross_income: Decimal
    annual_gross_tax: Decimal
    annual_deductions_base: Decimal
    annual_deduction_rate: Decimal
    annual_deductions_amount: Decimal
    annual_net_tax: Decimal
    total_monthly_withholdings_paid: Decimal
    fiscal_balance: Decimal  # > 0 a pagar, < 0 devolución a favor del trabajador
    notes: list[str] = []


def calculate_monthly_irpf_withholding(
    nominal: Decimal,
    social_security_contributions: Decimal,
    profile: TaxProfile,
    rules: IRPFRuleSet,
    bpc: BPCValue,
) -> IRPFWithholdingResult:
    """
    Simula la retención mensual de IRPF efectuada por el empleador (anticipo DGI).
    Aplica incremento ficto de aguinaldo del 6% (Dec. 148/007) y deducciones.
    """
    notes: list[str] = []

    # 1. Base gravada mensual con incremento ficto de aguinaldo del 6%
    ficto_multiplier = Decimal("1.0") + rules.sac_ficto_increment_rate
    base_with_ficto = (nominal * ficto_multiplier).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    base_in_bpc = base_with_ficto / bpc.value

    # 2. Impuesto Bruto por tramos progresivos
    gross_tax = Decimal("0.00")
    marginal_rate = Decimal("0.0000")

    for bracket in rules.brackets:
        if base_in_bpc > bracket.from_bpc:
            upper = bracket.to_bpc if bracket.to_bpc is not None else base_in_bpc
            taxable_bpc = min(base_in_bpc, upper) - bracket.from_bpc
            if taxable_bpc > Decimal("0"):
                taxable_uyu = (taxable_bpc * bpc.value).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                bracket_tax = (taxable_uyu * bracket.rate).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                gross_tax += bracket_tax
                if bracket.rate > marginal_rate:
                    marginal_rate = bracket.rate

    # 3. Base de deducciones (Aportes jubilatorios/salud + Cargas por hijos mensuales)
    monthly_children_bpc = (
        (
            Decimal(profile.children_count)
            * rules.child_deduction_annual_bpc
            * profile.child_deduction_share
        )
        + (
            Decimal(profile.disabled_children_count)
            * rules.disabled_child_deduction_annual_bpc
            * profile.child_deduction_share
        )
    ) / Decimal("12")

    children_deduction_uyu = (monthly_children_bpc * bpc.value).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    total_deductions_base = social_security_contributions + children_deduction_uyu

    # 4. Tasa de deducción según umbral de 15 BPC (Ley 20.124)
    threshold_deduction_uyu = rules.deduction_threshold_bpc * bpc.value
    deduction_rate = (
        rules.deduction_rate_low
        if nominal <= threshold_deduction_uyu
        else rules.deduction_rate_high
    )

    deductions_amount = (total_deductions_base * deduction_rate).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # 5. Retención neta (no puede ser negativa)
    net_withholding = max(Decimal("0.00"), gross_tax - deductions_amount)

    pct_ded = deduction_rate * Decimal("100")
    notes.append(
        f"Retención IRPF: Base ficto=${base_with_ficto} ({base_in_bpc:.2f} BPC). "
        f"Bruto=${gross_tax}, Deducciones=${deductions_amount} ({pct_ded}%)."
    )

    return IRPFWithholdingResult(
        taxable_base_monthly=nominal,
        taxable_base_with_ficto=base_with_ficto,
        gross_tax=gross_tax,
        deductions_base=total_deductions_base,
        deduction_rate=deduction_rate,
        deductions_amount=deductions_amount,
        net_withholding=net_withholding,
        marginal_rate=marginal_rate,
        notes=notes,
    )


def calculate_annual_irpf_settlement(
    annual_nominal_gross: Decimal,
    annual_social_security_contributions: Decimal,
    total_monthly_withholdings_paid: Decimal,
    profile: TaxProfile,
    rules: IRPFRuleSet,
    bpc: BPCValue,
) -> IRPFAnnualSettlementResult:
    """
    Realiza la liquidación y ajuste anual de IRPF (año civil) sobre ingresos reales.
    No aplica ficto del 6% ya que computa haberes reales efectivamente liquidados.
    """
    notes: list[str] = []
    annual_base_in_bpc = annual_nominal_gross / bpc.value

    # Escala anual (cada tramo en BPC multiplicado por 12)
    annual_gross_tax = Decimal("0.00")
    for bracket in rules.brackets:
        from_bpc_ann = bracket.from_bpc * Decimal("12")
        to_bpc_ann = (
            bracket.to_bpc * Decimal("12")
            if bracket.to_bpc is not None
            else annual_base_in_bpc
        )

        if annual_base_in_bpc > from_bpc_ann:
            upper = min(annual_base_in_bpc, to_bpc_ann)
            taxable_bpc = upper - from_bpc_ann
            if taxable_bpc > Decimal("0"):
                taxable_uyu = (taxable_bpc * bpc.value).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                bracket_tax = (taxable_uyu * bracket.rate).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                annual_gross_tax += bracket_tax

    # Deducciones anuales completas
    annual_children_bpc = (
        Decimal(profile.children_count)
        * rules.child_deduction_annual_bpc
        * profile.child_deduction_share
    ) + (
        Decimal(profile.disabled_children_count)
        * rules.disabled_child_deduction_annual_bpc
        * profile.child_deduction_share
    )
    annual_children_uyu = (annual_children_bpc * bpc.value).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    annual_deductions_base = annual_social_security_contributions + annual_children_uyu

    # Tasa anual según promedio mensual
    monthly_avg = annual_nominal_gross / Decimal("12")
    deduction_rate = (
        rules.deduction_rate_low
        if monthly_avg <= (rules.deduction_threshold_bpc * bpc.value)
        else rules.deduction_rate_high
    )

    annual_deductions_amount = (annual_deductions_base * deduction_rate).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    annual_net_tax = max(Decimal("0.00"), annual_gross_tax - annual_deductions_amount)

    # Saldo final contra retenciones mensuales pagadas
    fiscal_balance = annual_net_tax - total_monthly_withholdings_paid

    if fiscal_balance > Decimal("0"):
        notes.append(f"Saldo anual a pagar a DGI: ${fiscal_balance}")
    elif fiscal_balance < Decimal("0"):
        notes.append(
            f"Crédito/devolución IRPF a favor del trabajador: ${abs(fiscal_balance)}"
        )
    else:
        notes.append("Liquidación anual IRPF saldada exactamente con las retenciones.")

    return IRPFAnnualSettlementResult(
        annual_gross_income=annual_nominal_gross,
        annual_gross_tax=annual_gross_tax,
        annual_deductions_base=annual_deductions_base,
        annual_deduction_rate=deduction_rate,
        annual_deductions_amount=annual_deductions_amount,
        annual_net_tax=annual_net_tax,
        total_monthly_withholdings_paid=total_monthly_withholdings_paid,
        fiscal_balance=fiscal_balance,
        notes=notes,
    )
