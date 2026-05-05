"""
Controller para gestión de ingresos familiares
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from result import Result

from controllers.base_controller import BaseController
from core.unit_of_work import UnitOfWork
from models.errors import AppError
from models.income_model import Income
from repositories.income_repository import IncomeRepository
from services.domain.income_service import IncomeService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class IncomeController(BaseController):
    """
    Controller para gestión de ingresos.
    Soporta UoW inyectado para transacciones atómicas.
    """

    def __init__(
        self,
        session: Session | None = None,
        familia_id: int | None = None,
        uow: UnitOfWork | None = None,
    ) -> None:
        super().__init__(session=session, familia_id=familia_id, uow=uow)

    def get_title(self) -> str:
        return "Ingresos Familiares"

    def add_income(self, income: Income) -> Result[Income, AppError]:
        """Agregar un nuevo ingreso"""
        with self._get_session() as session:
            repo = IncomeRepository(session, self._familia_id)
            service = IncomeService(repo)
            return service.create_income(income)

    def list_incomes(self) -> list[Income]:
        """Listar todos los ingresos"""
        with self._get_session() as session:
            repo = IncomeRepository(session, self._familia_id)
            service = IncomeService(repo)
            return service.list_incomes()

    def list_by_member(self, member_id: int) -> list[Income]:
        """Listar ingresos de un miembro específico"""
        with self._get_session() as session:
            repo = IncomeRepository(session, self._familia_id)
            service = IncomeService(repo)
            return service.list_by_member(member_id)

    def list_for_month(self, year: int, month: int) -> list[Income]:
        """Ingresos del mes: recurrentes siempre + no-recurrentes solo del mes."""
        with self._get_session() as session:
            repo = IncomeRepository(session, self._familia_id)
            service = IncomeService(repo)
            return service.list_for_month(year, month)

    def get_summary_by_categories(
        self,
        year: int | None = None,
        month: int | None = None,
    ) -> dict[str, Decimal]:
        """Obtener resumen de ingresos por categoría del mes indicado."""
        with self._get_session() as session:
            repo = IncomeRepository(session, self._familia_id)
            service = IncomeService(repo)
            return service.get_summary_by_categories(year=year, month=month)

    def get_total_by_month(self, year: int, month: int) -> Decimal:
        """Obtener total de ingresos del mes"""
        with self._get_session() as session:
            repo = IncomeRepository(session, self._familia_id)
            service = IncomeService(repo)
            return service.get_total_by_month(year, month)

    def delete_income(self, income_id: int) -> Result[None, AppError]:
        """Eliminar un ingreso"""
        with self._get_session() as session:
            repo = IncomeRepository(session, self._familia_id)
            service = IncomeService(repo)
            return service.delete_income(income_id)

    def update_income(self, income: Income) -> Result[Income, AppError]:
        """Actualizar un ingreso existente"""
        with self._get_session() as session:
            repo = IncomeRepository(session, self._familia_id)
            service = IncomeService(repo)
            return service.update_income(income)
