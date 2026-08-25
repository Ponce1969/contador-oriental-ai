"""
Cálculo de aportes al Fondo Nacional de Salud (FONASA) - Ley 18.211 / Dec. 221/011.
Aritmética determinística 100% Decimal.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel

from services.labor.domain.enums import FonasaBeneficiaryType
from services.labor.domain.models import TaxProfile
from services.labor.domain.tax_rules import BPCValue, SocialSecurityRuleSet


class FonasaResult(BaseModel):
    """Resultado del cómputo de la cuota personal FONASA."""

    fonasa_amount: Decimal
    effective_rate: Decimal
    threshold_bpc_value: Decimal
    is_above_threshold: bool
    beneficiary_type: FonasaBeneficiaryType
    notes: list[str] = []


def calculate_fonasa(
    nominal: Decimal,
    profile: TaxProfile,
    rules: SocialSecurityRuleSet,
    bpc: BPCValue,
) -> FonasaResult:
    """
    Calcula el aporte al Seguro Nacional de Salud (FONASA) según la composición
    familiar del trabajador y el umbral de 2.5 BPC (sin computar aguinaldo).
    """
    threshold_amount = rules.fonasa_threshold_bpc * bpc.value
    is_above = nominal > threshold_amount

    rate_pair = rules.fonasa_rate_matrix.get(
        profile.fonasa_type,
        (Decimal("0.0300"), Decimal("0.0450")),
    )

    rate = rate_pair[1] if is_above else rate_pair[0]
    fonasa_amount = (nominal * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    cond_str = "superior" if is_above else "inferior/igual"
    pct = rate * Decimal("100")
    notes = [
        f"FONASA {pct}% aplicado ({profile.fonasa_type.value}, "
        f"{cond_str} a {rules.fonasa_threshold_bpc} BPC = ${threshold_amount})."
    ]

    return FonasaResult(
        fonasa_amount=fonasa_amount,
        effective_rate=rate,
        threshold_bpc_value=threshold_amount,
        is_above_threshold=is_above,
        beneficiary_type=profile.fonasa_type,
        notes=notes,
    )
