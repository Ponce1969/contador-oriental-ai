"""
Tests unitarios exhaustivos para el motor de cálculos laborales uruguayos.
Cumple con las directivas de python-testing-spec (determinismo, mutaciones, centésimos).
"""

from datetime import date
from decimal import Decimal

import pytest

from services.labor.domain.enums import (
    CalculationStatus,
    RemunerationType,
)
from services.labor.domain.models import CalculationRequest
from services.labor.domain.periods import AguinaldoPeriod
from services.labor.engine import LaborCalculationEngine


class TestAguinaldoPeriod:
    """Pruebas para la delimitación legal de períodos semestrales (Ley 12.840)."""

    def test_for_date_in_december_belongs_to_next_year_june_aguinaldo(self):
        period = AguinaldoPeriod.for_date(date(2025, 12, 15))
        assert period.year == 2026
        assert period.semester == 1
        assert period.payment_month == 6
        assert period.start_date == date(2025, 12, 1)
        assert period.end_date == date(2026, 5, 31)

    def test_for_date_in_march_belongs_to_current_year_june_aguinaldo(self):
        period = AguinaldoPeriod.for_date(date(2026, 3, 10))
        assert period.year == 2026
        assert period.semester == 1
        assert period.payment_month == 6

    def test_for_date_in_july_belongs_to_current_year_december_aguinaldo(self):
        period = AguinaldoPeriod.for_date(date(2026, 7, 20))
        assert period.year == 2026
        assert period.semester == 2
        assert period.payment_month == 12
        assert period.start_date == date(2026, 6, 1)
        assert period.end_date == date(2026, 11, 30)

    def test_for_semester_invalid_raises_value_error(self):
        with pytest.raises(ValueError, match="Semestre inválido"):
            AguinaldoPeriod.for_semester(2026, 3)

    def test_get_months_returns_correct_six_months_sequence(self):
        period_june = AguinaldoPeriod.for_semester(2026, 1)
        assert period_june.get_months() == [
            (2025, 12),
            (2026, 1),
            (2026, 2),
            (2026, 3),
            (2026, 4),
            (2026, 5),
        ]

        period_dec = AguinaldoPeriod.for_semester(2026, 2)
        assert period_dec.get_months() == [
            (2026, 6),
            (2026, 7),
            (2026, 8),
            (2026, 9),
            (2026, 10),
            (2026, 11),
        ]


class TestAguinaldoCalculator:
    """Pruebas del motor puro de aguinaldo."""

    def test_six_full_months_exact_calculation(self):
        """6 meses con sueldo fijo de $45.000 devengan exactamente $22.500."""
        request = CalculationRequest(
            familia_id=1,
            family_member_id=10,
            economic_activity_id=100,
            calculation_type="AGUINALDO_JUNIO",
            period_year=2026,
            period_semester=1,
            accrual_start=date(2025, 12, 1),
            accrual_end=date(2026, 5, 31),
            activity_start_date=date(2020, 1, 1),  # Antigüedad previa
            registered_incomes=[
                {
                    "id": 1,
                    "monto": Decimal("45000.00"),
                    "fecha": date(2025, 12, 5),
                    "concept": "salary",
                },
                {
                    "id": 2,
                    "monto": Decimal("45000.00"),
                    "fecha": date(2026, 1, 5),
                    "concept": "salary",
                },
                {
                    "id": 3,
                    "monto": Decimal("45000.00"),
                    "fecha": date(2026, 2, 5),
                    "concept": "salary",
                },
                {
                    "id": 4,
                    "monto": Decimal("45000.00"),
                    "fecha": date(2026, 3, 5),
                    "concept": "salary",
                },
                {
                    "id": 5,
                    "monto": Decimal("45000.00"),
                    "fecha": date(2026, 4, 5),
                    "concept": "salary",
                },
                {
                    "id": 6,
                    "monto": Decimal("45000.00"),
                    "fecha": date(2026, 5, 5),
                    "concept": "salary",
                },
            ],
        )

        result = LaborCalculationEngine.calculate_aguinaldo(
            request, today=date(2026, 6, 1)
        )

        assert result.status == CalculationStatus.CALCULATED
        assert result.total_computable == Decimal("270000.00")
        assert result.divisor == Decimal("12")
        assert result.final_amount == Decimal("22500.00")
        assert len(result.input_income_ids) == 6
        assert len(result.months_breakdown) == 6

    def test_half_period_entry_recent_hire(self):
        """Empleado contratado el 15/03/2026: solo computa Marzo, Abril y Mayo."""
        request = CalculationRequest(
            familia_id=1,
            family_member_id=10,
            economic_activity_id=100,
            calculation_type="AGUINALDO_JUNIO",
            period_year=2026,
            period_semester=1,
            accrual_start=date(2025, 12, 1),
            accrual_end=date(2026, 5, 31),
            activity_start_date=date(2026, 3, 15),  # Ingresó en Marzo
            registered_incomes=[
                {
                    "id": 1,
                    "monto": Decimal("45000.00"),
                    "fecha": date(2026, 3, 31),
                    "concept": "salary",
                },
                {
                    "id": 2,
                    "monto": Decimal("45000.00"),
                    "fecha": date(2026, 4, 30),
                    "concept": "salary",
                },
                {
                    "id": 3,
                    "monto": Decimal("45000.00"),
                    "fecha": date(2026, 5, 31),
                    "concept": "salary",
                },
            ],
        )

        result = LaborCalculationEngine.calculate_aguinaldo(
            request, today=date(2026, 6, 1)
        )

        assert result.status == CalculationStatus.CALCULATED
        # 3 meses * 45.000 = 135.000 / 12 = 11.250
        assert result.total_computable == Decimal("135000.00")
        assert result.final_amount == Decimal("11250.00")

    def test_missing_start_date_returns_insufficient_data(self):
        """Sin start_date, el motor devuelve INSUFFICIENT_DATA."""
        request = CalculationRequest(
            familia_id=1,
            family_member_id=10,
            economic_activity_id=100,
            calculation_type="AGUINALDO_JUNIO",
            period_year=2026,
            period_semester=1,
            accrual_start=date(2025, 12, 1),
            accrual_end=date(2026, 5, 31),
            activity_start_date=None,  # Faltante
        )

        result = LaborCalculationEngine.calculate_aguinaldo(request)

        assert result.status == CalculationStatus.INSUFFICIENT_DATA
        assert "start_date" in result.missing_fields
        assert result.final_amount == Decimal("0.00")

    def test_computable_vs_non_computable_concepts(self):
        """Horas extras y comisiones computan; aguinaldos previos no."""
        request = CalculationRequest(
            familia_id=1,
            family_member_id=10,
            economic_activity_id=100,
            calculation_type="AGUINALDO_DICIEMBRE",
            period_year=2026,
            period_semester=2,
            accrual_start=date(2026, 6, 1),
            accrual_end=date(2026, 11, 30),
            activity_start_date=date(2024, 1, 1),
            registered_incomes=[
                # Junio: Sueldo $50.000 + Horas extras $10.000 + Aguinaldo $25.000
                {
                    "id": 1,
                    "monto": Decimal("50000.00"),
                    "fecha": date(2026, 6, 5),
                    "concept": "salary",
                },
                {
                    "id": 2,
                    "monto": Decimal("10000.00"),
                    "fecha": date(2026, 6, 20),
                    "concept": "overtime",
                },
                {
                    "id": 3,
                    "monto": Decimal("25000.00"),
                    "fecha": date(2026, 6, 25),
                    "concept": "aguinaldo",
                },  # NO computable
                # Julio a Noviembre: Sueldo $50.000 cada mes
                {
                    "id": 4,
                    "monto": Decimal("50000.00"),
                    "fecha": date(2026, 7, 5),
                    "concept": "salary",
                },
                {
                    "id": 5,
                    "monto": Decimal("50000.00"),
                    "fecha": date(2026, 8, 5),
                    "concept": "salary",
                },
                {
                    "id": 6,
                    "monto": Decimal("50000.00"),
                    "fecha": date(2026, 9, 5),
                    "concept": "salary",
                },
                {
                    "id": 7,
                    "monto": Decimal("50000.00"),
                    "fecha": date(2026, 10, 5),
                    "concept": "salary",
                },
                {
                    "id": 8,
                    "monto": Decimal("50000.00"),
                    "fecha": date(2026, 11, 5),
                    "concept": "salary",
                },
            ],
        )

        result = LaborCalculationEngine.calculate_aguinaldo(
            request, today=date(2026, 12, 1)
        )

        # Total computable = (50.000 * 6) + 10.000 = 310.000
        assert result.total_computable == Decimal("310000.00")
        # 310.000 / 12 = 25.833,33
        assert result.final_amount == Decimal("25833.33")
        assert 3 not in result.input_income_ids  # El ID 3 de aguinaldo no se incluyó


    def test_unclassified_legacy_incomes_trigger_requires_review(self):
        """Un ingreso sin concepto en el período produce REQUIRES_REVIEW."""
        request = CalculationRequest(
            familia_id=1,
            family_member_id=10,
            economic_activity_id=100,
            calculation_type="AGUINALDO_JUNIO",
            period_year=2026,
            period_semester=1,
            accrual_start=date(2025, 12, 1),
            accrual_end=date(2026, 5, 31),
            activity_start_date=date(2020, 1, 1),
            registered_incomes=[
                {
                    "id": 1,
                    "monto": Decimal("45000.00"),
                    "fecha": date(2025, 12, 5),
                    "concept": "salary",
                },
                {
                    "id": 2,
                    "monto": Decimal("15000.00"),
                    "fecha": date(2026, 1, 15),
                    "concept": None,
                },  # Sin concepto
            ],
        )

        result = LaborCalculationEngine.calculate_aguinaldo(
            request, today=date(2026, 6, 1)
        )
        assert result.status == CalculationStatus.REQUIRES_REVIEW

    def test_future_months_projection_with_base_salary(self):
        """Meses futuros proyectados con sueldo base -> PROVISIONAL."""
        request = CalculationRequest(
            familia_id=1,
            family_member_id=10,
            economic_activity_id=100,
            calculation_type="AGUINALDO_JUNIO",
            period_year=2026,
            period_semester=1,
            accrual_start=date(2025, 12, 1),
            accrual_end=date(2026, 5, 31),
            activity_start_date=date(2020, 1, 1),
            estimated_base_salary=Decimal("60000.00"),
            registered_incomes=[
                {
                    "id": 1,
                    "monto": Decimal("60000.00"),
                    "fecha": date(2025, 12, 5),
                    "concept": "salary",
                },
                {
                    "id": 2,
                    "monto": Decimal("60000.00"),
                    "fecha": date(2026, 1, 5),
                    "concept": "salary",
                },
                {
                    "id": 3,
                    "monto": Decimal("60000.00"),
                    "fecha": date(2026, 2, 5),
                    "concept": "salary",
                },
                {
                    "id": 4,
                    "monto": Decimal("60000.00"),
                    "fecha": date(2026, 3, 5),
                    "concept": "salary",
                },
            ],
        )

        # Hoy es 15 de marzo de 2026: abril (4) y mayo (5) son futuros
        result = LaborCalculationEngine.calculate_aguinaldo(
            request, today=date(2026, 3, 15)
        )

        assert result.status == CalculationStatus.PROVISIONAL
        # 4 meses reales (240k) + 2 proyectados a 60k (120k) = 360k / 12 = 30k
        assert result.total_computable == Decimal("360000.00")
        assert result.final_amount == Decimal("30000.00")



class TestVacationPayCalculator:
    """Pruebas del motor puro de salario vacacional orientativo (Ley 16.101)."""

    def test_monthly_standard_calculation(self):
        """Sueldo mensual $60.000 por 20 días: ($60.000 / 30) * 20 = $40.000."""
        request = CalculationRequest(
            familia_id=1,
            family_member_id=10,
            economic_activity_id=100,
            calculation_type="SALARIO_VACACIONAL",
            period_year=2026,
            period_semester=1,
            accrual_start=date(2026, 1, 1),
            accrual_end=date(2026, 12, 31),
            estimated_base_salary=Decimal("60000.00"),
            requested_vacation_days=20,
        )

        result = LaborCalculationEngine.calculate_vacation_pay(
            request, remuneration_type=RemunerationType.MENSUAL
        )

        assert result.status == CalculationStatus.CALCULATED
        assert result.final_amount == Decimal("40000.00")
        assert result.divisor == Decimal("30")

    def test_jornalero_triggers_requires_review(self):
        """Jornaleros requieren promedio anual de jornales -> REQUIRES_REVIEW."""
        request = CalculationRequest(
            familia_id=1,
            family_member_id=10,
            economic_activity_id=100,
            calculation_type="SALARIO_VACACIONAL",
            period_year=2026,
            period_semester=1,
            accrual_start=date(2026, 1, 1),
            accrual_end=date(2026, 12, 31),
            estimated_base_salary=Decimal("2500.00"),
            requested_vacation_days=20,
        )

        result = LaborCalculationEngine.calculate_vacation_pay(
            request, remuneration_type=RemunerationType.JORNALERO
        )
        assert result.status == CalculationStatus.REQUIRES_REVIEW
