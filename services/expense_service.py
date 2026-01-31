"""
Servicio de lógica de negocio para gastos familiares
"""

from __future__ import annotations

from result import Err, Result

from models.errors import DatabaseError, ValidationError
from models.expense_model import Expense
from repositories.expense_repository import ExpenseRepository


class ExpenseService:
    """Servicio para gestión de gastos con validaciones de negocio"""
    
    def __init__(self, repo: ExpenseRepository) -> None:
        self._repo = repo

    def create_expense(
        self, expense: Expense
    ) -> Result[Expense, ValidationError | DatabaseError]:
        """Crear un nuevo gasto con validaciones"""
        
        # Validación: monto debe ser positivo
        if expense.monto <= 0:
            return Err(ValidationError(message="El monto debe ser mayor a 0"))
        
        # Validación: descripción no puede estar vacía
        if not expense.descripcion or expense.descripcion.strip() == "":
            return Err(ValidationError(message="La descripción es obligatoria"))
        
        # Validación: si es recurrente, debe tener frecuencia
        if expense.es_recurrente and not expense.frecuencia:
            return Err(
                ValidationError(
                    message="Los gastos recurrentes deben tener frecuencia"
                )
            )
        
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
        
        # Validación: debe tener ID
        if expense.id is None:
            return Err(ValidationError(message="El gasto debe tener un ID"))
        
        # Validación: monto debe ser positivo
        if expense.monto <= 0:
            return Err(ValidationError(message="El monto debe ser mayor a 0"))
        
        # Validación: descripción no puede estar vacía
        if not expense.descripcion or expense.descripcion.strip() == "":
            return Err(ValidationError(message="La descripción es obligatoria"))
        
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
