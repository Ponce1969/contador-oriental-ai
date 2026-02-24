"""
BaseRepository genérico para el Contador Oriental
Elimina duplicación de CRUD en todos los repositorios
"""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy.orm import Session

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """
    Repositorio base genérico que provee operaciones CRUD comunes.
    
    Usa Generics de Python para funcionar con cualquier modelo:
    - ExpenseRepository(BaseRepository[Expense])
    - IncomeRepository(BaseRepository[Income])
    - FamilyMemberRepository(BaseRepository[FamilyMember])
    
    Automáticamente filtra por familia_id si el modelo tiene ese atributo.
    """
    
    def __init__(self, session: Session, model: type[T], familia_id: int | None = None):
        self.session = session
        self.model = model
        self.familia_id = familia_id

    def get_by_id(self, id: int) -> T | None:
        """
        Obtener un registro por su ID.
        
        Args:
            id: ID del registro a buscar
            
        Returns:
            El registro encontrado o None
        """
        query = self.session.query(self.model).filter(self.model.id == id)
        
        # Filtrar por familia si el modelo tiene family_id
        if self.familia_id and hasattr(self.model, 'family_id'):
            query = query.filter(self.model.family_id == self.familia_id)
            
        return query.first()

    def get_all(self) -> list[T]:
        """
        Obtener todos los registros del modelo.
        
        Returns:
            Lista de todos los registros (filtrados por familia si aplica)
        """
        query = self.session.query(self.model)
        
        # Filtrar por familia si el modelo tiene family_id
        if self.familia_id and hasattr(self.model, 'family_id'):
            query = query.filter(self.model.family_id == self.familia_id)
            
        return query.all()

    def add(self, entity: T) -> T:
        """
        Agregar un nuevo registro.
        
        Args:
            entity: Entidad a agregar
            
        Returns:
            La entidad guardada con ID asignado
        """
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity

    def update(self, entity: T) -> T:
        """
        Actualizar un registro existente.
        
        Args:
            entity: Entidad con datos actualizados
            
        Returns:
            La entidad actualizada
        """
        self.session.merge(entity)
        self.session.commit()
        return entity

    def delete(self, id: int) -> bool:
        """
        Eliminar un registro por ID.
        
        Args:
            id: ID del registro a eliminar
            
        Returns:
            True si se eliminó, False si no se encontró
        """
        obj = self.get_by_id(id)
        if obj:
            self.session.delete(obj)
            self.session.commit()
            return True
        return False

    def count(self) -> int:
        """
        Contar todos los registros.
        
        Returns:
            Cantidad de registros (filtrados por familia si aplica)
        """
        query = self.session.query(self.model)
        
        # Filtrar por familia si el modelo tiene family_id
        if self.familia_id and hasattr(self.model, 'family_id'):
            query = query.filter(self.model.family_id == self.familia_id)
            
        return query.count()

    def get_active(self) -> list[T]:
        """
        Obtener registros activos (si el modelo tiene campo 'active').
        
        Returns:
            Lista de registros activos
        """
        query = self.session.query(self.model)
        
        # Filtrar por familia si el modelo tiene family_id
        if self.familia_id and hasattr(self.model, 'family_id'):
            query = query.filter(self.model.family_id == self.familia_id)
            
        # Filtrar por activo si el modelo tiene el campo
        if hasattr(self.model, 'active'):
            query = query.filter(self.model.active == True)
            
        return query.all()
