"""
Controller para gestión de gastos familiares
"""

from __future__ import annotations

import logging

from result import Ok, Result

from controllers.base_controller import BaseController
from core.events import Event, EventType, event_system
from models.errors import AppError
from models.expense_model import Expense
from repositories.expense_repository import ExpenseRepository
from services.domain.expense_service import ExpenseService

logger = logging.getLogger(__name__)


class ExpenseController(BaseController):
    """
    Controller para página de gastos
    """

    def get_title(self) -> str:
        return "Gastos Familiares"

    def add_expense(self, expense: Expense) -> Result[Expense, AppError]:
        """Agregar un nuevo gasto y publicar evento para memoria vectorial (fire-and-forget)"""
        with self._get_session() as session:
            repo = ExpenseRepository(session, self._familia_id)
            service = ExpenseService(repo)
            result = service.create_expense(expense)

        if isinstance(result, Ok):
            gasto = result.ok()
            event = Event(
                type=EventType.GASTO_CREADO,
                familia_id=self._familia_id or 0,
                source_id=gasto.id,
                data={
                    "descripcion": gasto.descripcion,
                    "monto": float(gasto.monto),
                    "categoria": gasto.categoria.value,
                    "metodo_pago": gasto.metodo_pago.value,
                    "fecha": str(gasto.fecha),
                    "recurrente": gasto.es_recurrente,
                },
            )
            event_system.fire_and_forget(event)

        return result

    def list_expenses(self) -> list[Expense]:
        """Listar todos los gastos (sin filtro)"""
        with self._get_session() as session:
            repo = ExpenseRepository(session, self._familia_id)
            service = ExpenseService(repo)
            return service.list_expenses()

    def list_expenses_by_month(self, year: int, month: int) -> list[Expense]:
        """Listar gastos de un mes específico"""
        with self._get_session() as session:
            repo = ExpenseRepository(session, self._familia_id)
            service = ExpenseService(repo)
            return service.list_by_month(year, month)

    def list_by_category(self, categoria: str) -> list[Expense]:
        """Listar gastos por categoría"""
        with self._get_session() as session:
            repo = ExpenseRepository(session, self._familia_id)
            service = ExpenseService(repo)
            return service.list_by_category(categoria)

    def get_summary_by_categories(
        self,
        year: int | None = None,
        month: int | None = None,
    ) -> dict[str, float]:
        """Obtener resumen de gastos por categoría del mes indicado."""
        with self._get_session() as session:
            repo = ExpenseRepository(session, self._familia_id)
            service = ExpenseService(repo)
            return service.get_summary_by_categories(year=year, month=month)

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
