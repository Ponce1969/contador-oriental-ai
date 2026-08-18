"""
Controller para la gestión de actividades económicas y cálculos laborales familiares.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from result import Result

from controllers.base_controller import BaseController
from core.unit_of_work import UnitOfWork
from models.errors import AppError
from repositories.economic_activity_repository import EconomicActivityRepository
from repositories.income_repository import IncomeRepository
from services.domain.labor_service import LaborService
from services.labor.domain.models import CalculationResult, EconomicActivity

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class LaborController(BaseController):
    """Controller para actividades económicas y beneficios laborales."""

    def __init__(
        self,
        session: Session | None = None,
        familia_id: int | None = None,
        uow: UnitOfWork | None = None,
    ) -> None:
        super().__init__(session=session, familia_id=familia_id, uow=uow)

    def get_title(self) -> str:
        return "Actividades y Beneficios Laborales"

    def add_activity(
        self, activity: EconomicActivity
    ) -> Result[EconomicActivity, AppError]:
        """Agregar una nueva actividad económica."""
        with self._get_session() as session:
            activity_repo = EconomicActivityRepository(session, self._familia_id)
            income_repo = IncomeRepository(session, self._familia_id)
            service = LaborService(activity_repo, income_repo)
            return service.create_activity(activity)

    def get_activity(self, activity_id: int) -> Result[EconomicActivity, AppError]:
        """Obtener una actividad económica por ID."""
        with self._get_session() as session:
            activity_repo = EconomicActivityRepository(session, self._familia_id)
            income_repo = IncomeRepository(session, self._familia_id)
            service = LaborService(activity_repo, income_repo)
            return service.get_activity(activity_id)

    def list_by_member(self, member_id: int) -> list[EconomicActivity]:
        """Listar actividades de un integrante."""
        with self._get_session() as session:
            activity_repo = EconomicActivityRepository(session, self._familia_id)
            income_repo = IncomeRepository(session, self._familia_id)
            service = LaborService(activity_repo, income_repo)
            return service.list_activities_by_member(member_id)

    def list_all_activities(self) -> list[EconomicActivity]:
        """Listar todas las actividades de la familia."""
        with self._get_session() as session:
            activity_repo = EconomicActivityRepository(session, self._familia_id)
            income_repo = IncomeRepository(session, self._familia_id)
            service = LaborService(activity_repo, income_repo)
            return service.list_all_activities()

    def update_activity(
        self, activity: EconomicActivity
    ) -> Result[EconomicActivity, AppError]:
        """Actualizar una actividad económica."""
        with self._get_session() as session:
            activity_repo = EconomicActivityRepository(session, self._familia_id)
            income_repo = IncomeRepository(session, self._familia_id)
            service = LaborService(activity_repo, income_repo)
            return service.update_activity(activity)

    def delete_activity(self, activity_id: int) -> Result[None, AppError]:
        """Eliminar una actividad económica."""
        with self._get_session() as session:
            activity_repo = EconomicActivityRepository(session, self._familia_id)
            income_repo = IncomeRepository(session, self._familia_id)
            service = LaborService(activity_repo, income_repo)
            return service.delete_activity(activity_id)

    def calculate_aguinaldo(
        self,
        activity_id: int,
        year: int,
        semester: int,
        today: date | None = None,
    ) -> Result[CalculationResult, AppError]:
        """Calcular aguinaldo para una actividad económica."""
        with self._get_session() as session:
            activity_repo = EconomicActivityRepository(session, self._familia_id)
            income_repo = IncomeRepository(session, self._familia_id)
            service = LaborService(activity_repo, income_repo)
            return service.calculate_member_aguinaldo(
                activity_id, year, semester, today=today
            )

    def calculate_vacation_pay(
        self,
        activity_id: int,
        requested_days: int = 20,
    ) -> Result[CalculationResult, AppError]:
        """Calcular salario vacacional orientativo para una actividad económica."""
        with self._get_session() as session:
            activity_repo = EconomicActivityRepository(session, self._familia_id)
            income_repo = IncomeRepository(session, self._familia_id)
            service = LaborService(activity_repo, income_repo)
            return service.calculate_member_vacation_pay(
                activity_id, requested_days=requested_days
            )
