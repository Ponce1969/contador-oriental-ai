"""
Controller para gestión de gastos familiares
"""

from __future__ import annotations

from result import Result

from controllers.base_controller import BaseController
from models.errors import AppError
from models.expense_model import Expense
from repositories.expense_repository import ExpenseRepository
from services.expense_service import ExpenseService


class ExpenseController(BaseController):
    """
    Controller para página de gastos
    """

    def get_title(self) -> str:
        return "Gastos Familiares"

    def add_expense(self, expense: Expense) -> Result[Expense, AppError]:
        """Agregar un nuevo gasto"""
        with self._get_session() as session:
            repo = ExpenseRepository(session, self._familia_id)
            service = ExpenseService(repo)
            return service.create_expense(expense)

    def list_expenses(self) -> list[Expense]:
        """Listar todos los gastos"""
        with self._get_session() as session:
            repo = ExpenseRepository(session, self._familia_id)
            service = ExpenseService(repo)
            return service.list_expenses()

    def list_by_category(self, categoria: str) -> list[Expense]:
        """Listar gastos por categoría"""
        with self._get_session() as session:
            repo = ExpenseRepository(session, self._familia_id)
            service = ExpenseService(repo)
            return service.list_by_category(categoria)

    def get_summary_by_categories(self) -> dict[str, float]:
        """Obtener resumen de gastos por categoría"""
        with self._get_session() as session:
            repo = ExpenseRepository(session, self._familia_id)
            service = ExpenseService(repo)
            return service.get_summary_by_categories()

    def update_expense(self, expense: Expense) -> Result[Expense, AppError]:
        """Actualizar un gasto existente"""
        with self._get_session() as session:
            repo = ExpenseRepository(session, self._familia_id)
            service = ExpenseService(repo)
            return service.update_expense(expense)

    def delete_expense(self, expense_id: int) -> Result[None, AppError]:
        """Eliminar un gasto"""
        with self._get_session() as session:
            repo = ExpenseRepository(session, self._familia_id)
            service = ExpenseService(repo)
            return service.delete_expense(expense_id)

    def get_total_by_month(self, year: int, month: int) -> float:
        """Obtener total de gastos de un mes específico"""
        with self._get_session() as session:
            repo = ExpenseRepository(session, self._familia_id)
            service = ExpenseService(repo)
            return service.get_total_by_month(year, month)
