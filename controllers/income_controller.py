"""
Controller para gestión de ingresos familiares
"""

from __future__ import annotations

from result import Result

from controllers.base_controller import BaseController
from models.errors import AppError
from models.income_model import Income
from repositories.income_repository import IncomeRepository
from services.income_service import IncomeService


class IncomeController(BaseController):
    """Controller para gestión de ingresos"""

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

    def get_summary_by_categories(self) -> dict[str, float]:
        """Obtener resumen de ingresos por categoría"""
        with self._get_session() as session:
            repo = IncomeRepository(session, self._familia_id)
            service = IncomeService(repo)
            return service.get_summary_by_categories()

    def get_total_by_month(self, year: int, month: int) -> float:
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
