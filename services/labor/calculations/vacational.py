"""
Motor puro de cálculo orientativo de Salario Vacacional según normativa uruguaya.
Regla: UY-MTSS-VAC-2026-v1 (Ley 16.101 y Decretos reglamentarios).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from services.labor.domain.enums import CalculationStatus, RemunerationType
from services.labor.domain.models import CalculationRequest, CalculationResult

RULE_VERSION_VACACIONAL = "UY-MTSS-VAC-2026-v1"


class VacationPayCalculator:
    """Calculador orientativo y auditable de Salario Vacacional (Ley 16.101)."""

    @staticmethod
    def calculate(
        request: CalculationRequest,
        remuneration_type: RemunerationType = RemunerationType.MENSUAL,
    ) -> CalculationResult:
        """
        Ejecuta el cálculo orientativo de salario vacacional por días solicitados.

        Aritmética 100% en Python con Decimal. Cero float.
        """
        requested_days = Decimal(str(request.requested_vacation_days))

        # 1. Validación de datos mínimos requeridos
        salary = request.estimated_base_salary
        if salary is None or salary <= Decimal("0.00"):
            # Si no hay base declarada, buscar el último sueldo registrado
            valid_salaries = [
                Decimal(str(inc["monto"]))
                for inc in request.registered_incomes
                if inc.get("concept") in {"salary", None}
                and Decimal(str(inc["monto"])) > 0
            ]
            if valid_salaries:
                salary = valid_salaries[-1]
            else:
                return CalculationResult(
                    request_summary={
                        "familia_id": request.familia_id,
                        "family_member_id": request.family_member_id,
                        "economic_activity_id": request.economic_activity_id,
                        "requested_days": request.requested_vacation_days,
                    },
                    rule_version=RULE_VERSION_VACACIONAL,
                    status=CalculationStatus.INSUFFICIENT_DATA,
                    missing_fields=["base_salary"],
                    explanation_notes=[
                        "No es posible calcular el salario vacacional sin sueldo base."
                    ],
                )

        # 2. Caso Jornalero o Situación Variable
        if remuneration_type == RemunerationType.JORNALERO:
            return CalculationResult(
                request_summary={
                    "familia_id": request.familia_id,
                    "family_member_id": request.family_member_id,
                    "economic_activity_id": request.economic_activity_id,
                    "requested_days": request.requested_vacation_days,
                },
                rule_version=RULE_VERSION_VACACIONAL,
                status=CalculationStatus.REQUIRES_REVIEW,
                total_computable=salary,
                divisor=Decimal("25"),
                final_amount=Decimal("0.00"),
                explanation_notes=[
                    "El cálculo para jornaleros requiere computar el promedio anual "
                    "de jornales efectivamente trabajados (Ley 16.101)."
                ],
            )

        # 3. Caso Mensual Estándar (Ley 16.101: 100% jornal líquido)
        divisor = Decimal("30")
        jornal_liquido = (salary / divisor).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        final_amount = (jornal_liquido * requested_days).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return CalculationResult(
            request_summary={
                "familia_id": request.familia_id,
                "family_member_id": request.family_member_id,
                "economic_activity_id": request.economic_activity_id,
                "requested_days": request.requested_vacation_days,
            },
            rule_version=RULE_VERSION_VACACIONAL,
            status=CalculationStatus.CALCULATED,
            currency="UYU",
            input_income_ids=[],
            months_breakdown=[],
            total_computable=salary,
            divisor=divisor,
            final_amount=final_amount,
            missing_fields=[],
            explanation_notes=[
                f"Estimación orientativa para {request.requested_vacation_days} días "
                f"de licencia sobre sueldo de ${salary:.2f} "
                f"(Jornal: ${jornal_liquido:.2f}/día) según Ley 16.101."
            ],
        )
