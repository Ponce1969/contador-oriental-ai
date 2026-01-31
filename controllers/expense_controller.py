"""
Controller para gestión de gastos familiares
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from result import Result
from sqlalchemy.orm import Session

from core.sqlalchemy_session import get_db_session
from models.errors import AppError
from models.expense_model import Expense
from repositories.expense_repository import ExpenseRepository
from services.expense_service import ExpenseService


class ExpenseController:
    """
    Controller para página de gastos
    """

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    @contextmanager
    def _get_session(self) -> Generator[Session, None, None]:
        """Obtener sesión de base de datos."""
        if self._session:
            yield self._session
        else:
            with get_db_session() as session:
                yield session

    def get_title(self) -> str:
        return "Gastos Familiares"

    def add_expense(self, expense: Expense) -> Result[Expense, AppError]:
        """Agregar un nuevo gasto"""
        with self._get_session() as session:
            repo = ExpenseRepository(session)
            service = ExpenseService(repo)
            return service.create_expense(expense)

    def list_expenses(self) -> list[Expense]:
        """Listar todos los gastos"""
        with self._get_session() as session:
            repo = ExpenseRepository(session)
            service = ExpenseService(repo)
            return service.list_expenses()

    def list_by_category(self, categoria: str) -> list[Expense]:
        """Listar gastos por categoría"""
        with self._get_session() as session:
            repo = ExpenseRepository(session)
            service = ExpenseService(repo)
            return service.list_by_category(categoria)

    def get_summary_by_categories(self) -> dict[str, float]:
        """Obtener resumen de gastos por categoría"""
        with self._get_session() as session:
            repo = ExpenseRepository(session)
            service = ExpenseService(repo)
            return service.get_summary_by_categories()

    def delete_expense(self, expense_id: int) -> Result[None, AppError]:
        """Eliminar un gasto"""
        with self._get_session() as session:
            repo = ExpenseRepository(session)
            service = ExpenseService(repo)
            return service.delete_expense(expense_id)

    def get_total_by_month(self, year: int, month: int) -> Result[float, AppError]:
        """Obtener total de gastos de un mes específico"""
        with self._get_session() as session:
            repo = ExpenseRepository(session)
            service = ExpenseService(repo)
            return service.get_total_by_month(year, month)
