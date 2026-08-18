"""
Motor de dominio y orquestador para cálculos laborales uruguayos.
"""

from __future__ import annotations

from datetime import date

from services.labor.calculations.aguinaldo import AguinaldoCalculator
from services.labor.calculations.vacational import VacationPayCalculator
from services.labor.domain.enums import RemunerationType
from services.labor.domain.models import CalculationRequest, CalculationResult


class LaborCalculationEngine:
    """Orquestador de cálculos determinísticos del subdominio laboral."""

    @staticmethod
    def calculate_aguinaldo(
        request: CalculationRequest, today: date | None = None
    ) -> CalculationResult:
        """Calcula el aguinaldo (fracción Junio o Diciembre) con trazabilidad."""
        return AguinaldoCalculator.calculate(request, today=today)

    @staticmethod
    def calculate_vacation_pay(
        request: CalculationRequest,
        remuneration_type: RemunerationType = RemunerationType.MENSUAL,
    ) -> CalculationResult:
        """Calcula el salario vacacional orientativo para días solicitados."""
        return VacationPayCalculator.calculate(
            request, remuneration_type=remuneration_type
        )

