"""
Cálculo de Anticipos Bimestrales de IRPF Cat. II para Servicios Personales.
(Título 7 T.O. 1996 Art. 34 / Dec. 148/007 Art. 62).
Aritmética determinística 100% Decimal.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel

from services.labor.domain.tax_rules import IRPFIndependentRuleSet


class IRPFIndependentAdvanceResult(BaseModel):
    """Resultado del cálculo de anticipo bimestral de IRPF."""

    bimonthly_gross_billed: Decimal
    expense_deduction_amount: Decimal
    is_actual_expense_applied: bool
    taxable_base: Decimal
    gross_advance_amount: Decimal
    withholdings_suffered: Decimal
    net_advance_payable: Decimal
    notes: list[str] = []


def calculate_bimonthly_irpf_advance(
    bimonthly_billed_without_vat: Decimal,
    rules: IRPFIndependentRuleSet,
    withholdings_suffered: Decimal = Decimal("0.00"),
    actual_documented_expenses: Decimal | None = None,
) -> IRPFIndependentAdvanceResult:
    """
    Calcula el anticipo bimestral de IRPF considerando deducción ficta (30%) o real.
    """
    notes: list[str] = []

    if actual_documented_expenses is not None:
        is_actual = True
        expense_deduction = actual_documented_expenses
        taxable_base = max(
            Decimal("0.00"), bimonthly_billed_without_vat - expense_deduction
        )
        notes.append(
            f"Deducción de gastos reales documentados: ${expense_deduction} UYU."
        )
    else:
        is_actual = False
        expense_deduction = (
            bimonthly_billed_without_vat * rules.standard_expense_deduction_rate
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        taxable_base = bimonthly_billed_without_vat - expense_deduction
        notes.append(
            f"Deducción 30% (${expense_deduction} UYU). Base 70%: ${taxable_base} UYU."
        )

    gross_advance = (taxable_base * rules.bimonthly_advance_rate).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    net_advance = max(Decimal("0.00"), gross_advance - withholdings_suffered)

    pct = rules.bimonthly_advance_rate * Decimal("100")
    notes.append(
        f"Anticipo IRPF ({pct}%): Bruto=${gross_advance}, "
        f"Ret=${withholdings_suffered}, Neto=${net_advance}."
    )

    return IRPFIndependentAdvanceResult(
        bimonthly_gross_billed=bimonthly_billed_without_vat,
        expense_deduction_amount=expense_deduction,
        is_actual_expense_applied=is_actual,
        taxable_base=taxable_base,
        gross_advance_amount=gross_advance,
        withholdings_suffered=withholdings_suffered,
        net_advance_payable=net_advance,
        notes=notes,
    )
