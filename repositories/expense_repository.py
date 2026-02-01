"""
Repository para gestión de gastos familiares
"""

from __future__ import annotations

from collections.abc import Sequence

from result import Err, Ok, Result
from sqlalchemy.orm import Session

from database.tables import ExpenseTable
from models.errors import DatabaseError
from models.expense_model import Expense
from repositories.mappers import to_domain, to_table


class ExpenseRepository:
    """Repository para operaciones CRUD de gastos"""
    
    def __init__(self, session: Session, familia_id: int | None = None) -> None:
        self._session = session
        self._familia_id = familia_id

    def add(self, expense: Expense) -> Result[Expense, DatabaseError]:
        """Agregar un nuevo gasto"""
        try:
            table_row = to_table(expense)
            # Agregar familia_id si está configurado
            if self._familia_id is not None:
                table_row.familia_id = self._familia_id
            self._session.add(table_row)
            self._session.flush()
            
            created = to_domain(table_row)
            return Ok(created)
        except Exception as e:
            return Err(DatabaseError(message=f"Error al guardar gasto: {e}"))

    def get_all(self) -> Sequence[Expense]:
        """Obtener todos los gastos de la familia"""
        query = self._session.query(ExpenseTable)
        if self._familia_id is not None:
            query = query.filter(ExpenseTable.familia_id == self._familia_id)
        rows = query.all()
        return [to_domain(row) for row in rows]

    def get_by_id(self, expense_id: int) -> Result[Expense, DatabaseError]:
        """Obtener un gasto por ID de la familia"""
        try:
            query = self._session.query(ExpenseTable).filter(
                ExpenseTable.id == expense_id
            )
            if self._familia_id is not None:
                query = query.filter(ExpenseTable.familia_id == self._familia_id)
            row = query.first()
            
            if row is None:
                return Err(DatabaseError(message=f"Gasto {expense_id} no encontrado"))
            
            return Ok(to_domain(row))
        except Exception as e:
            return Err(DatabaseError(message=f"Error al buscar gasto: {e}"))

    def get_by_category(self, categoria: str) -> Sequence[Expense]:
        """Obtener gastos por categoría de la familia"""
        query = self._session.query(ExpenseTable).filter(
            ExpenseTable.categoria == categoria
        )
        if self._familia_id is not None:
            query = query.filter(ExpenseTable.familia_id == self._familia_id)
        rows = query.all()
        return [to_domain(row) for row in rows]

    def get_by_month(self, year: int, month: int) -> Sequence[Expense]:
        """Obtener gastos de un mes específico de la familia"""
        from sqlalchemy import extract
        
        query = self._session.query(ExpenseTable).filter(
            extract('year', ExpenseTable.fecha) == year,
            extract('month', ExpenseTable.fecha) == month
        )
        if self._familia_id is not None:
            query = query.filter(ExpenseTable.familia_id == self._familia_id)
        rows = query.all()
        return [to_domain(row) for row in rows]

    def delete(self, expense_id: int) -> Result[None, DatabaseError]:
        """Eliminar un gasto de la familia"""
        try:
            query = self._session.query(ExpenseTable).filter(
                ExpenseTable.id == expense_id
            )
            if self._familia_id is not None:
                query = query.filter(ExpenseTable.familia_id == self._familia_id)
            row = query.first()
            
            if row is None:
                return Err(DatabaseError(message=f"Gasto {expense_id} no encontrado"))
            
            self._session.delete(row)
            self._session.flush()
            return Ok(None)
        except Exception as e:
            return Err(DatabaseError(message=f"Error al eliminar gasto: {e}"))

    def update(self, expense: Expense) -> Result[Expense, DatabaseError]:
        """Actualizar un gasto existente de la familia"""
        try:
            if expense.id is None:
                return Err(DatabaseError(message="El gasto debe tener un ID"))
            
            query = self._session.query(ExpenseTable).filter(
                ExpenseTable.id == expense.id
            )
            if self._familia_id is not None:
                query = query.filter(ExpenseTable.familia_id == self._familia_id)
            row = query.first()
            
            if row is None:
                return Err(DatabaseError(message=f"Gasto {expense.id} no encontrado"))
            
            # Actualizar campos
            row.monto = expense.monto
            row.fecha = expense.fecha
            row.descripcion = expense.descripcion
            row.categoria = expense.categoria.value
            row.subcategoria = expense.subcategoria
            row.metodo_pago = expense.metodo_pago.value
            row.es_recurrente = expense.es_recurrente
            row.frecuencia = (
                expense.frecuencia_recurrencia.value
                if expense.frecuencia_recurrencia
                else None
            )
            row.notas = expense.notas
            
            self._session.flush()
            return Ok(to_domain(row))
        except Exception as e:
            return Err(DatabaseError(message=f"Error al actualizar gasto: {e}"))
