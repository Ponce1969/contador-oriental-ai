"""
Servicio de lógica de negocio para gastos familiares
"""

from __future__ import annotations

from result import Result

from constants.messages import ValidationMessages
from models.errors import DatabaseError, ValidationError
from models.expense_model import Expense
from repositories.expense_repository import ExpenseRepository
from services.validators import (
    validate_descripcion_requerida,
    validate_id_requerido,
    validate_monto_positivo,
    validate_recurrente_con_frecuencia,
)


class ExpenseService:
    """Servicio para gestión de gastos con validaciones de negocio"""
    
    def __init__(self, repo: ExpenseRepository) -> None:
        self._repo = repo

    def create_expense(
        self, expense: Expense
    ) -> Result[Expense, ValidationError | DatabaseError]:
        """Crear un nuevo gasto con validaciones"""
        for check in (
            validate_monto_positivo(expense.monto),
            validate_descripcion_requerida(expense.descripcion),
            validate_recurrente_con_frecuencia(
                expense.es_recurrente,
                expense.frecuencia_recurrencia,
                ValidationMessages.RECURRENTE_SIN_FRECUENCIA_GASTO,
            ),
        ):
            if check.is_err():
                return check  # type: ignore[return-value]
        return self._repo.add(expense)

    def list_expenses(self) -> list[Expense]:
        """Listar todos los gastos"""
        expenses = self._repo.get_all()
        return list(expenses)

    def get_expense(self, expense_id: int) -> Result[Expense, DatabaseError]:
        """Obtener un gasto por ID"""
        return self._repo.get_by_id(expense_id)

    def list_by_category(self, categoria: str) -> list[Expense]:
        """Listar gastos por categoría"""
        expenses = self._repo.get_by_category(categoria)
        return list(expenses)

    def list_by_month(self, year: int, month: int) -> list[Expense]:
        """Listar gastos de un mes específico"""
        expenses = self._repo.get_by_month(year, month)
        return list(expenses)

    def delete_expense(self, expense_id: int) -> Result[None, DatabaseError]:
        """Eliminar un gasto"""
        return self._repo.delete(expense_id)

    def update_expense(
        self, expense: Expense
    ) -> Result[Expense, ValidationError | DatabaseError]:
        """Actualizar un gasto existente con validaciones"""
        for check in (
            validate_id_requerido(expense.id, ValidationMessages.ID_REQUERIDO_GASTO),
            validate_monto_positivo(expense.monto),
            validate_descripcion_requerida(expense.descripcion),
        ):
            if check.is_err():
                return check  # type: ignore[return-value]
        return self._repo.update(expense)

    def get_total_by_category(self, categoria: str) -> float:
        """Calcular total gastado en una categoría"""
        expenses = self.list_by_category(categoria)
        return sum(expense.monto for expense in expenses)

    def get_total_by_month(self, year: int, month: int) -> float:
        """Calcular total gastado en un mes"""
        expenses = self.list_by_month(year, month)
        return sum(expense.monto for expense in expenses)

    def get_summary_by_categories(self) -> dict[str, float]:
        """Obtener resumen de gastos por categoría"""
        expenses = self.list_expenses()
        summary: dict[str, float] = {}
        
        for expense in expenses:
            categoria = expense.categoria.value
            summary[categoria] = summary.get(categoria, 0.0) + expense.monto
        
        return summary
