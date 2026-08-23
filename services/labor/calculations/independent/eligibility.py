"""
Evaluador de elegibilidad para Servicios Personales (Fase 3A).
Valida condiciones fácticas antes de permitir el cálculo tributario.
"""

from __future__ import annotations

from services.labor.domain.dtos import (
    EligibilityEvaluation,
    IndependentProfile,
)
from services.labor.domain.enums import (
    EligibilityStatus,
    IndependentTaxRegime,
    PensionFundType,
)


class PersonalServicesEligibilityEvaluator:
    """Evalúa si el perfil cumple las condiciones fácticas de Servicios Personales."""

    @staticmethod
    def evaluate(profile: IndependentProfile) -> EligibilityEvaluation:
        violations: list[str] = []
        review_reasons: list[str] = []

        if profile.regime != IndependentTaxRegime.SERVICIOS_PERSONALES:
            violations.append(
                f"El régimen '{profile.regime}' no es Servicios Personales."
            )

        if profile.is_professional is None:
            violations.append(
                "Debe declararse si la actividad es profesional o no profesional."
            )

        if profile.pension_fund is None:
            violations.append(
                "Debe seleccionarse la caja de previsión social (BPS o CJPPU)."
            )

        if profile.pension_fund == PensionFundType.CJPPU:
            if profile.cjppu_category is None:
                violations.append(
                    "Para CJPPU debe indicarse categoría de aportación (1 a 10)."
                )
            elif not (1 <= profile.cjppu_category <= 10):
                violations.append(
                    f"Categoría CJPPU '{profile.cjppu_category}' fuera de rango (1-10)."
                )

        if profile.opt_for_actual_expenses:
            review_reasons.append(
                "Deducción por gastos reales requiere respaldo contable formal."
            )

        if violations:
            return EligibilityEvaluation(
                status=EligibilityStatus.INELIGIBLE,
                violations=violations,
                review_reasons=review_reasons,
                can_proceed_to_calculation=False,
            )

        status = (
            EligibilityStatus.REQUIRES_REVIEW
            if review_reasons
            else EligibilityStatus.ELIGIBLE
        )

        return EligibilityEvaluation(
            status=status,
            violations=[],
            review_reasons=review_reasons,
            can_proceed_to_calculation=True,
        )
