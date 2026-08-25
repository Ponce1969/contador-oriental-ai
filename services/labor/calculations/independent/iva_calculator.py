"""
Cálculo de IVA para Servicios Personales (Título 10 T.O. 1996 / Dec. 220/998).
Aritmética determinística 100% Decimal (cero float).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel

from services.labor.domain.tax_rules import IVARuleSet


class VATCalculationResult(BaseModel):
    """Resultado del cálculo de IVA para facturación de servicios personales."""

    net_billed_amount: Decimal
    vat_rate_applied: Decimal
    vat_gross_amount: Decimal
    withholding_cede_amount: Decimal
    vat_net_payable: Decimal
    is_client_cede: bool
    notes: list[str] = []


def calculate_personal_services_vat(
    net_billed_amount: Decimal,
    rules: IVARuleSet,
    rate_type: str = "BASIC",
    is_client_cede: bool = False,
) -> VATCalculationResult:
    """
    Calcula el IVA devengado y la retención CEDE (60% del IVA) si corresponde.
    """
    notes: list[str] = []
    rate = rules.basic_rate if rate_type == "BASIC" else rules.minimum_rate

    vat_gross = (net_billed_amount * rate).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    withholding = Decimal("0.00")
    if is_client_cede and vat_gross > Decimal("0.00"):
        withholding = (vat_gross * rules.cede_withholding_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        notes.append(f"Retención CEDE 60% aplicada (Dec. 94/002): ${withholding} UYU.")

    net_payable = max(Decimal("0.00"), vat_gross - withholding)

    notes.append(
        f"IVA {rate * Decimal('100')}% sobre facturación neta de ${net_billed_amount}: "
        f"IVA=${vat_gross}, A pagar DGI=${net_payable}."
    )

    return VATCalculationResult(
        net_billed_amount=net_billed_amount,
        vat_rate_applied=rate,
        vat_gross_amount=vat_gross,
        withholding_cede_amount=withholding,
        vat_net_payable=net_payable,
        is_client_cede=is_client_cede,
        notes=notes,
    )
