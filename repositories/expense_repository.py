"""
Repository para gestión de gastos familiares
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from database.tables import ExpenseTable
from models.expense_model import Expense
from repositories.base_table_repository import BaseTableRepository
from repositories.mappers import to_domain, to_table


class ExpenseRepository(BaseTableRepository[Expense, ExpenseTable]):
    """Repository para operaciones CRUD de gastos"""
    
    def __init__(self, session: Session, familia_id: int | None = None) -> None:
        super().__init__(session, ExpenseTable, familia_id)

    def _to_domain(self, table_row):
        """Convertir tabla ExpenseTable a dominio Expense"""
        return to_domain(table_row)
    
    def _to_table(self, expense):
        """Convertir dominio Expense a tabla ExpenseTable"""
        return to_table(expense)

    def _update_specific_fields(self, table_row, expense: Expense) -> None:
        """Actualizar campos específicos de gastos."""
        table_row.categoria = expense.categoria.value
        table_row.subcategoria = expense.subcategoria
        table_row.metodo_pago = expense.metodo_pago.value
        table_row.es_recurrente = expense.es_recurrente
        table_row.frecuencia = (
            expense.frecuencia_recurrencia.value
            if expense.frecuencia_recurrencia
            else None
        )

    def get_by_category(self, categoria: str) -> Sequence[Expense]:
        """Obtener gastos por categoría de la familia"""
        query = self.session.query(ExpenseTable).filter(
            ExpenseTable.categoria == categoria
        )
        query = self._filter_by_family(query)
        rows = query.all()
        return [to_domain(row) for row in rows]

    def get_by_month(self, year: int, month: int) -> Sequence[Expense]:
        """Obtener gastos de un mes específico de la familia"""
        from sqlalchemy import extract
        
        query = self.session.query(ExpenseTable).filter(
            extract('year', ExpenseTable.fecha) == year,
            extract('month', ExpenseTable.fecha) == month
        )
        query = self._filter_by_family(query)
        rows = query.all()
        return [to_domain(row) for row in rows]

