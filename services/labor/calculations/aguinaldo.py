"""
Motor puro de cálculo de Aguinaldo (Sueldo Anual Complementario) uruguayo.
Regla: UY-MTSS-SAC-2026-v1 (Ley 12.840, 14.525 y Decretos reglamentarios).
"""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from services.labor.domain.enums import CalculationStatus, IncomeConcept
from services.labor.domain.models import (
    CalculationRequest,
    CalculationResult,
    ComputableMonth,
)
from services.labor.domain.periods import AguinaldoPeriod

RULE_VERSION_AGUINALDO = "UY-MTSS-SAC-2026-v1"
COMPUTABLE_CONCEPTS = {
    IncomeConcept.SALARY.value,
    IncomeConcept.OVERTIME.value,
    IncomeConcept.COMMISSION.value,
    "salary",
    "overtime",
    "commission",
}
NON_COMPUTABLE_CONCEPTS = {
    IncomeConcept.AGUINALDO.value,
    IncomeConcept.SALARIO_VACACIONAL.value,
    "aguinaldo",
    "vacation_pay",
}


class AguinaldoCalculator:
    """Calculador determinístico de Aguinaldo para trabajadores dependientes."""

    @staticmethod
    def calculate(
        request: CalculationRequest, today: date | None = None
    ) -> CalculationResult:
        """
        Ejecuta el cálculo de aguinaldo para el período especificado en el request.

        Aritmética 100% en Python con Decimal. Cero float. Cero dependencias externas.
        """
        if today is None:
            today = date.today()

        missing_fields: list[str] = []
        explanation_notes: list[str] = []

        # 1. Validación de datos mínimos requeridos
        if request.activity_start_date is None:
            missing_fields.append("start_date")
            return CalculationResult(
                request_summary={
                    "familia_id": request.familia_id,
                    "family_member_id": request.family_member_id,
                    "economic_activity_id": request.economic_activity_id,
                    "period_year": request.period_year,
                    "period_semester": request.period_semester,
                },
                rule_version=RULE_VERSION_AGUINALDO,
                status=CalculationStatus.INSUFFICIENT_DATA,
                missing_fields=missing_fields,
                explanation_notes=[
                    "No es posible calcular el aguinaldo sin fecha de inicio laboral."
                ],
            )

        period = AguinaldoPeriod.for_semester(
            request.period_year, request.period_semester
        )
        months_list = period.get_months()

        months_breakdown: list[ComputableMonth] = []
        input_income_ids: list[int] = []
        has_provisional_months = False
        has_unclassified_incomes = False

        # Agrupar ingresos registrados por (year, month)
        incomes_by_month: dict[tuple[int, int], list[dict]] = {}
        for inc in request.registered_incomes:
            inc_date: date = (
                inc["fecha"]
                if isinstance(inc["fecha"], date)
                else date.fromisoformat(str(inc["fecha"]))
            )
            key = (inc_date.year, inc_date.month)
            incomes_by_month.setdefault(key, []).append(inc)

        total_computable = Decimal("0.00")

        # 2. Iterar sobre cada uno de los 6 meses del semestre
        for y, m in months_list:
            # ¿El mes es anterior a la fecha de inicio laboral del empleado?
            if (y < request.activity_start_date.year) or (
                y == request.activity_start_date.year
                and m < request.activity_start_date.month
            ):
                months_breakdown.append(
                    ComputableMonth(
                        year=y, month=m, monto=Decimal("0.00"), es_proyectado=False
                    )
                )
                continue

            # ¿El mes es posterior a la fecha de cese laboral (si existe)?
            if request.activity_end_date and (
                (y > request.activity_end_date.year)
                or (
                    y == request.activity_end_date.year
                    and m > request.activity_end_date.month
                )
            ):
                months_breakdown.append(
                    ComputableMonth(
                        year=y, month=m, monto=Decimal("0.00"), es_proyectado=False
                    )
                )
                continue

            month_incomes = incomes_by_month.get((y, m), [])
            month_total = Decimal("0.00")
            month_income_ids: list[int] = []

            if month_incomes:
                for inc in month_incomes:
                    concept = inc.get("concept")
                    monto = Decimal(str(inc["monto"]))
                    inc_id = inc.get("id")

                    if concept in COMPUTABLE_CONCEPTS:
                        month_total += monto
                        if inc_id is not None:
                            month_income_ids.append(inc_id)
                            input_income_ids.append(inc_id)
                    elif concept is None or concept == "legacy_unclassified":
                        has_unclassified_incomes = True
                        explanation_notes.append(
                            f"Ingreso de {y}-{m:02d} por ${monto:.2f} "
                            "sin concepto clasificado requiere revisión."
                        )

                months_breakdown.append(
                    ComputableMonth(
                        year=y,
                        month=m,
                        monto=month_total,
                        es_proyectado=False,
                        income_ids=month_income_ids,
                    )
                )
                total_computable += month_total
            else:
                # El mes no tiene ingresos registrados
                is_future = (y > today.year) or (y == today.year and m > today.month)
                if is_future:
                    if (
                        request.estimated_base_salary is not None
                        and request.estimated_base_salary > 0
                    ):
                        projected_salary = request.estimated_base_salary
                        months_breakdown.append(
                            ComputableMonth(
                                year=y,
                                month=m,
                                monto=projected_salary,
                                es_proyectado=True,
                            )
                        )
                        total_computable += projected_salary
                        has_provisional_months = True
                    else:
                        months_breakdown.append(
                            ComputableMonth(
                                year=y,
                                month=m,
                                monto=Decimal("0.00"),
                                es_proyectado=True,
                            )
                        )
                        has_provisional_months = True
                else:
                    # Mes pasado sin ingresos
                    months_breakdown.append(
                        ComputableMonth(
                            year=y, month=m, monto=Decimal("0.00"), es_proyectado=False
                        )
                    )

        # 3. Determinar estado del cálculo
        divisor = Decimal("12")
        final_amount = (total_computable / divisor).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        if has_unclassified_incomes:
            status = CalculationStatus.REQUIRES_REVIEW
        elif has_provisional_months:
            status = CalculationStatus.PROVISIONAL
            explanation_notes.append(
                "Cálculo estimado: incluye meses futuros proyectados con sueldo base."
            )
        else:
            status = CalculationStatus.CALCULATED
            explanation_notes.append(
                f"Cálculo exacto (${total_computable:.2f} / 12) Ley 12.840."
            )

        return CalculationResult(
            request_summary={
                "familia_id": request.familia_id,
                "family_member_id": request.family_member_id,
                "economic_activity_id": request.economic_activity_id,
                "period_year": request.period_year,
                "period_semester": request.period_semester,
                "payment_month": period.payment_month,
            },
            rule_version=RULE_VERSION_AGUINALDO,
            status=status,
            currency="UYU",
            input_income_ids=input_income_ids,
            months_breakdown=months_breakdown,
            total_computable=total_computable,
            divisor=divisor,
            final_amount=final_amount,
            missing_fields=[],
            explanation_notes=explanation_notes,
        )
