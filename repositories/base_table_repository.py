"""
BaseTableRepository para el patrón con mappers (ExpenseTable, IncomeTable, etc.)
Elimina duplicación de CRUD en repositorios que usan mappers
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Generic, TypeVar

from result import Err, Ok, Result
from sqlalchemy.orm import Session

from models.errors import DatabaseError

T = TypeVar('T')  # Domain model (Expense, Income, etc.)
TTable = TypeVar('TTable')  # SQLAlchemy table (ExpenseTable, IncomeTable, etc.)


class BaseTableRepository(ABC, Generic[T, TTable]):
    """
    Repositorio base para el patrón con mappers.
    
    Provee operaciones CRUD comunes usando:
    - Domain models (Expense, Income) para la capa de negocio
    - SQLAlchemy tables (ExpenseTable, IncomeTable) para persistencia
    - Mappers (to_domain, to_table) para conversión
    
    Automáticamente filtra por familia_id si la tabla tiene ese campo.
    """
    
    def __init__(
        self, 
        session: Session, 
        table_model: type[TTable], 
        familia_id: int | None = None
    ):
        self.session = session
        self.table_model = table_model
        self.familia_id = familia_id

    @abstractmethod
    def _to_domain(self, table_row):
        """Convertir tabla a dominio - debe ser implementado por subclase"""
        pass
    
    @abstractmethod
    def _to_table(self, entity):
        """Convertir dominio a tabla - debe ser implementado por subclase"""
        pass

    def _filter_by_family(self, query):
        """Aplica filtro por familia_id si está configurado y la tabla lo tiene."""
        if self.familia_id is not None and hasattr(self.table_model, 'familia_id'):
            return query.filter(self.table_model.familia_id == self.familia_id)
        return query

    def add(self, entity: T) -> Result[T, DatabaseError]:
        """Agregar un nuevo registro."""
        try:
            table_row = self._to_table(entity)
            # Agregar familia_id si está configurado
            if self.familia_id is not None and hasattr(table_row, 'familia_id'):
                table_row.familia_id = self.familia_id
            self.session.add(table_row)
            self.session.flush()
            
            created = self._to_domain(table_row)
            return Ok(created)
        except Exception as e:
            return Err(DatabaseError(message=f"Error al guardar: {e}"))

    def get_all(self) -> Sequence[T]:
        """Obtener todos los registros."""
        query = self.session.query(self.table_model)
        query = self._filter_by_family(query)
        rows = query.all()
        return [self._to_domain(row) for row in rows]

    def get_by_id(self, entity_id: int) -> Result[T, DatabaseError]:
        """Obtener un registro por ID."""
        try:
            query = self.session.query(self.table_model).filter(
                self.table_model.id == entity_id
            )
            query = self._filter_by_family(query)
            row = query.first()
            
            if row is None:
                return Err(DatabaseError(message=f"Registro {entity_id} no encontrado"))
            
            return Ok(self._to_domain(row))
        except Exception as e:
            return Err(DatabaseError(message=f"Error al buscar: {e}"))

    def delete(self, entity_id: int) -> Result[None, DatabaseError]:
        """Eliminar un registro por ID."""
        try:
            query = self.session.query(self.table_model).filter(
                self.table_model.id == entity_id
            )
            query = self._filter_by_family(query)
            row = query.first()
            
            if row is None:
                return Err(DatabaseError(message=f"Registro {entity_id} no encontrado"))
            
            self.session.delete(row)
            self.session.flush()
            return Ok(None)
        except Exception as e:
            return Err(DatabaseError(message=f"Error al eliminar: {e}"))

    def update(self, entity: T) -> Result[T, DatabaseError]:
        """Actualizar un registro existente."""
        try:
            if not hasattr(entity, 'id') or entity.id is None:
                return Err(DatabaseError(message="La entidad debe tener un ID"))
            
            query = self.session.query(self.table_model).filter(
                self.table_model.id == entity.id
            )
            query = self._filter_by_family(query)
            row = query.first()
            
            if row is None:
                return Err(DatabaseError(message=f"Registro {entity.id} no encontrado"))
            
            # Actualizar campos comunes
            if hasattr(entity, 'monto'):
                row.monto = entity.monto
            if hasattr(entity, 'fecha'):
                row.fecha = entity.fecha
            if hasattr(entity, 'descripcion'):
                row.descripcion = entity.descripcion
            if hasattr(entity, 'notas'):
                row.notas = entity.notas
            
            # Las subclases deben implementar actualizaciones específicas
            self._update_specific_fields(row, entity)
            
            self.session.flush()
            return Ok(self._to_domain(row))
        except Exception as e:
            return Err(DatabaseError(message=f"Error al actualizar: {e}"))

    def _update_specific_fields(self, table_row, entity: T):
        """
        Las subclases deben sobreescribir este método para actualizar campos específicos.
        Ejemplo: row.categoria = entity.categoria.value
        """
        pass
