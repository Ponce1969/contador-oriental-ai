"""
Servicio de dominio para la gestión laboral y cálculo de beneficios de integrantes familiares.
"""

from __future__ import annotations

from datetime import date

from result import Err, Ok, Result

from models.errors import DatabaseError, ValidationError
from repositories.economic_activity_repository import EconomicActivityRepository
from repositories.income_repository import IncomeRepository
from services.labor.domain.enums import RemunerationType
from services.labor.domain.models import (
    CalculationRequest,
    CalculationResult,
    EconomicActivity,
)
from services.labor.domain.periods import AguinaldoPeriod
from services.labor.engine import LaborCalculationEngine


class LaborService:
    """Servicio de dominio para actividades económicas y beneficios laborales."""

    def __init__(
        self,
        activity_repo: EconomicActivityRepository,
        income_repo: IncomeRepository,
    ) -> None:
        self._activity_repo = activity_repo
        self._income_repo = income_repo

    def create_activity(
        self, activity: EconomicActivity
    ) -> Result[EconomicActivity, ValidationError | DatabaseError]:
        """Crear una nueva actividad económica con validaciones."""
        if not activity.title.strip():
            return Err(ValidationError(message="El título o descripción de la actividad es requerido."))
        if activity.family_member_id <= 0:
            return Err(ValidationError(message="El integrante familiar es requerido."))

        return self._activity_repo.add(activity)

    def get_activity(self, activity_id: int) -> Result[EconomicActivity, DatabaseError]:
        """Obtener una actividad económica por ID."""
        return self._activity_repo.get_by_id(activity_id)

    def list_activities_by_member(self, member_id: int) -> list[EconomicActivity]:
        """Listar actividades de un integrante familiar."""
        return self._activity_repo.list_by_member(member_id)

    def list_all_activities(self) -> list[EconomicActivity]:
        """Listar todas las actividades económicas de la familia."""
        return self._activity_repo.list_all_by_family()

    def update_activity(
        self, activity: EconomicActivity
    ) -> Result[EconomicActivity, ValidationError | DatabaseError]:
        """Actualizar una actividad económica existente."""
        if activity.id is None:
            return Err(ValidationError(message="ID requerido para actualizar la actividad."))
        if not activity.title.strip():
            return Err(ValidationError(message="El título o descripción de la actividad es requerido."))

        return self._activity_repo.update(activity)

    def delete_activity(self, activity_id: int) -> Result[None, DatabaseError]:
        """Eliminar una actividad económica."""
        return self._activity_repo.delete(activity_id)

    def calculate_member_aguinaldo(
        self,
        activity_id: int,
        year: int,
        semester: int,
        today: date | None = None,
    ) -> Result[CalculationResult, ValidationError | DatabaseError]:
        """
        Ejecuta el cálculo determinístico de aguinaldo para una actividad económica.
        """
        activity_res = self._activity_repo.get_by_id(activity_id)
        if activity_res.is_err():
            return activity_res  # type: ignore[return-value]

        activity = activity_res.unwrap()
        period = AguinaldoPeriod.for_semester(year, semester)

        # Obtener los ingresos del miembro en el período
        all_member_incomes = self._income_repo.get_by_member(activity.family_member_id)

        # Filtrar los que caen dentro del período de devengamiento del aguinaldo
        period_incomes: list[dict] = []
        for inc in all_member_incomes:
            # Si el ingreso está asociado a otra actividad económica distinta, omitirlo
            if inc.economic_activity_id is not None and inc.economic_activity_id != activity.id:
                continue

            if period.start_date <= inc.fecha <= period.end_date:
                period_incomes.append(
                    {
                        "id": inc.id,
                        "monto": inc.monto,
                        "fecha": inc.fecha,
                        "concept": inc.concept,
                    }
                )

        estimated_base = None
        if activity.dependent_details and activity.dependent_details.estimated_monthly_nominal:
            estimated_base = activity.dependent_details.estimated_monthly_nominal

        request = CalculationRequest(
            familia_id=activity.familia_id,
            family_member_id=activity.family_member_id,
            economic_activity_id=activity.id,
            calculation_type=f"AGUINALDO_{'JUNIO' if semester == 1 else 'DICIEMBRE'}",
            period_year=year,
            period_semester=semester,
            accrual_start=period.start_date,
            accrual_end=period.end_date,
            activity_start_date=activity.start_date,
            activity_end_date=activity.end_date,
            estimated_base_salary=estimated_base,
            registered_incomes=period_incomes,
        )

        result = LaborCalculationEngine.calculate_aguinaldo(request, today=today)
        return Ok(result)

    def calculate_member_vacation_pay(
        self,
        activity_id: int,
        requested_days: int = 20,
    ) -> Result[CalculationResult, ValidationError | DatabaseError]:
        """
        Ejecuta el cálculo orientativo de salario vacacional para una actividad económica.
        """
        activity_res = self._activity_repo.get_by_id(activity_id)
        if activity_res.is_err():
            return activity_res  # type: ignore[return-value]

        activity = activity_res.unwrap()
        all_member_incomes = self._income_repo.get_by_member(activity.family_member_id)

        incomes_data = [
            {
                "id": inc.id,
                "monto": inc.monto,
                "fecha": inc.fecha,
                "concept": inc.concept,
            }
            for inc in all_member_incomes
            if inc.economic_activity_id in {None, activity.id}
        ]

        estimated_base = None
        rem_type = RemunerationType.MENSUAL
        if activity.dependent_details:
            estimated_base = activity.dependent_details.estimated_monthly_nominal
            rem_type = activity.dependent_details.remuneration_type

        request = CalculationRequest(
            familia_id=activity.familia_id,
            family_member_id=activity.family_member_id,
            economic_activity_id=activity.id,
            calculation_type="SALARIO_VACACIONAL",
            period_year=date.today().year,
            period_semester=1,
            accrual_start=date(date.today().year, 1, 1),
            accrual_end=date(date.today().year, 12, 31),
            activity_start_date=activity.start_date,
            estimated_base_salary=estimated_base,
            registered_incomes=incomes_data,
            requested_vacation_days=requested_days,
        )

        result = LaborCalculationEngine.calculate_vacation_pay(request, remuneration_type=rem_type)
        return Ok(result)
