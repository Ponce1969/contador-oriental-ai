"""
Cálculo de aportes a la Seguridad Social (Montepío y FRL) - BPS / INEFOP.
Aritmética determinística 100% Decimal.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel

from services.labor.domain.tax_rules import SocialSecurityRuleSet


class SocialSecurityResult(BaseModel):
    """Resultado del cómputo de Montepío y Fondo de Reconversión Laboral."""

    montepio_amount: Decimal
    montepio_rate: Decimal
    frl_amount: Decimal
    frl_rate: Decimal
    total_amount: Decimal
    exceeds_cap: bool = False
    cap_applied_nominal: Decimal | None = None
    notes: list[str] = []


def calculate_social_security(
    nominal: Decimal,
    rules: SocialSecurityRuleSet,
) -> SocialSecurityResult:
    """
    Calcula Montepío (15%) y FRL (0.10%) sobre el salario nominal gravado.

    Guarda: Si el nominal supera el tope máximo de BPS/AFAP, se marca exceeds_cap=True
    para exigir revisión del régimen previsional (Ley 16.713 / Ley 20.130).
    """
    notes: list[str] = []
    exceeds_cap = False
    cap_nominal = rules.bps_max_contribution_cap_nominal

    if cap_nominal is not None and nominal > cap_nominal:
        exceeds_cap = True
        notes.append(
            f"Nominal (${nominal}) supera tope jubilatorio BPS (${cap_nominal}). "
            "Requiere tramos AFAP Ley 16.713/20.130."
        )

    # Cálculo con quantize ROUND_HALF_UP centésimo a centésimo
    montepio = (nominal * rules.montepio_rate).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    frl = (nominal * rules.frl_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = montepio + frl

    return SocialSecurityResult(
        montepio_amount=montepio,
        montepio_rate=rules.montepio_rate,
        frl_amount=frl,
        frl_rate=rules.frl_rate,
        total_amount=total,
        exceeds_cap=exceeds_cap,
        cap_applied_nominal=cap_nominal,
        notes=notes,
    )
