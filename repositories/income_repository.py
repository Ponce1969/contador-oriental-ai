"""
Repository para gestión de ingresos familiares
"""

from __future__ import annotations

from collections.abc import Sequence

from result import Err, Ok, Result
from sqlalchemy.orm import Session

from database.tables import IncomeTable
from models.errors import DatabaseError
from models.income_model import Income
from repositories.income_mappers import income_to_domain, income_to_table


class IncomeRepository:
    """Repository para operaciones CRUD de ingresos"""
    
    def __init__(self, session: Session, familia_id: int | None = None) -> None:
        self._session = session
        self._familia_id = familia_id

    def add(self, income: Income) -> Result[Income, DatabaseError]:
        """Agregar un nuevo ingreso"""
        try:
            table_row = income_to_table(income)
            # Agregar familia_id si está configurado
            if self._familia_id is not None:
                table_row.familia_id = self._familia_id
            self._session.add(table_row)
            self._session.flush()
            
            created = income_to_domain(table_row)
            return Ok(created)
        except Exception as e:
            return Err(DatabaseError(message=f"Error al guardar ingreso: {e}"))

    def get_all(self) -> Sequence[Income]:
        """Obtener todos los ingresos de la familia"""
        query = self._session.query(IncomeTable)
        if self._familia_id is not None:
            query = query.filter(IncomeTable.familia_id == self._familia_id)
        rows = query.all()
        return [income_to_domain(row) for row in rows]

    def get_by_id(self, income_id: int) -> Result[Income, DatabaseError]:
        """Obtener un ingreso por ID de la familia"""
        try:
            query = self._session.query(IncomeTable).filter(
                IncomeTable.id == income_id
            )
            if self._familia_id is not None:
                query = query.filter(IncomeTable.familia_id == self._familia_id)
            row = query.first()
            
            if row is None:
                return Err(DatabaseError(message=f"Ingreso {income_id} no encontrado"))
            
            return Ok(income_to_domain(row))
        except Exception as e:
            return Err(DatabaseError(message=f"Error al buscar ingreso: {e}"))

    def get_by_member(self, member_id: int) -> Sequence[Income]:
        """Obtener ingresos de un miembro específico de la familia"""
        query = self._session.query(IncomeTable).filter(
            IncomeTable.family_member_id == member_id
        )
        if self._familia_id is not None:
            query = query.filter(IncomeTable.familia_id == self._familia_id)
        rows = query.all()
        return [income_to_domain(row) for row in rows]

    def get_by_month(self, year: int, month: int) -> Sequence[Income]:
        """Obtener ingresos de un mes específico de la familia"""
        from sqlalchemy import extract
        
        query = self._session.query(IncomeTable).filter(
            extract('year', IncomeTable.fecha) == year,
            extract('month', IncomeTable.fecha) == month
        )
        if self._familia_id is not None:
            query = query.filter(IncomeTable.familia_id == self._familia_id)
        rows = query.all()
        return [income_to_domain(row) for row in rows]

    def delete(self, income_id: int) -> Result[None, DatabaseError]:
        """Eliminar un ingreso de la familia"""
        try:
            query = self._session.query(IncomeTable).filter(
                IncomeTable.id == income_id
            )
            if self._familia_id is not None:
                query = query.filter(IncomeTable.familia_id == self._familia_id)
            row = query.first()
            
            if row is None:
                return Err(DatabaseError(message=f"Ingreso {income_id} no encontrado"))
            
            self._session.delete(row)
            self._session.flush()
            return Ok(None)
        except Exception as e:
            return Err(DatabaseError(message=f"Error al eliminar ingreso: {e}"))

    def update(self, income: Income) -> Result[Income, DatabaseError]:
        """Actualizar un ingreso existente de la familia"""
        try:
            if income.id is None:
                return Err(DatabaseError(message="El ingreso debe tener un ID"))
            
            query = self._session.query(IncomeTable).filter(
                IncomeTable.id == income.id
            )
            if self._familia_id is not None:
                query = query.filter(IncomeTable.familia_id == self._familia_id)
            row = query.first()
            
            if row is None:
                return Err(DatabaseError(message=f"Ingreso {income.id} no encontrado"))
            
            # Actualizar campos
            row.family_member_id = income.family_member_id
            row.monto = income.monto
            row.fecha = income.fecha
            row.descripcion = income.descripcion
            row.categoria = income.categoria.value
            row.es_recurrente = income.es_recurrente
            row.frecuencia = income.frecuencia.value if income.frecuencia else None
            row.notas = income.notas
            
            self._session.flush()
            return Ok(income_to_domain(row))
        except Exception as e:
            return Err(DatabaseError(message=f"Error al actualizar ingreso: {e}"))
