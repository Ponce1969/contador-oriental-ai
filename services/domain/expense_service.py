"""
Servicio de lógica de negocio para gastos familiares
"""

from __future__ import annotations

from decimal import Decimal

from result import Err, Result

from constants.messages import ValidationMessages
from models.errors import DatabaseError, ValidationError
from models.expense_model import Expense
from repositories.expense_repository import ExpenseRepository
from services.domain.validators import (
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
                expense.frecuencia,
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
        """Eliminar un gasto (preserva historial de cuotas con SET NULL)"""
        # Verificar si el gasto tiene compra en cuotas asociada
        expense_result = self._repo.get_by_id(expense_id)
        if isinstance(expense_result, Err):
            return expense_result

        expense = expense_result.ok()
        if expense.installment_purchase_id:
            # No bloquear eliminación, ON DELETE SET NULL se encarga
            # El historial de cuotas queda preservado
            pass

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

    def get_total_by_category(self, categoria: str) -> Decimal:
        """Calcular total gastado en una categoría"""
        expenses = self.list_by_category(categoria)
        return sum((expense.monto for expense in expenses), Decimal("0"))

    def get_total_by_month(self, year: int, month: int) -> Decimal:
        """Calcular total gastado en un mes"""
        expenses = self.list_by_month(year, month)
        return sum((expense.monto for expense in expenses), Decimal("0"))

    def get_summary_by_categories(
        self,
        year: int | None = None,
        month: int | None = None,
    ) -> dict[str, Decimal]:
        """Obtener resumen de gastos por categoría, opcionalmente filtrado por mes."""
        if year is not None and month is not None:
            expenses = self.list_by_month(year, month)
        else:
            expenses = self.list_expenses()
        summary: dict[str, Decimal] = {}
        for expense in expenses:
            categoria = expense.categoria.value
            summary[categoria] = summary.get(categoria, Decimal("0")) + expense.monto
        return summary
