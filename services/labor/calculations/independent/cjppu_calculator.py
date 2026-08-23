"""
Cálculo de Aportes a la Caja Profesional de Profesionales Universitarios (CJPPU).
(Ley 17.738 Art. 60 / Ley 20.212).
Aritmética determinística 100% Decimal.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel

from services.labor.domain.tax_rules import CJPPURuleSet


class CJPPUCalculationResult(BaseModel):
    """Resultado del cálculo de aportes mensuales a CJPPU."""

    category: int
    fictitious_salary: Decimal
    contribution_rate: Decimal
    monthly_contribution_amount: Decimal
    notes: list[str] = []


def calculate_cjppu_contribution(
    category: int,
    rules: CJPPURuleSet,
) -> CJPPUCalculationResult:
    """
    Calcula el aporte mensual obligatorio a CJPPU según la categoría trienal (1 a 10).
    """
    fictitious_salary = rules.category_fictitious_salaries.get(
        category, Decimal("0.00")
    )
    monthly_amount = (fictitious_salary * rules.contribution_rate).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    pct = rules.contribution_rate * Decimal("100")
    notes = [
        f"Aporte CJPPU Cat. {category} (Ficto ${fictitious_salary}, {pct}%): "
        f"${monthly_amount} UYU/mes."
    ]

    return CJPPUCalculationResult(
        category=category,
        fictitious_salary=fictitious_salary,
        contribution_rate=rules.contribution_rate,
        monthly_contribution_amount=monthly_amount,
        notes=notes,
    )
