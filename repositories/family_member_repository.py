"""
Repository para gestión de miembros de la familia
"""

from __future__ import annotations

from collections.abc import Sequence

from result import Err, Ok, Result
from sqlalchemy.orm import Session

from database.tables import FamilyMemberTable
from models.errors import DatabaseError
from models.family_member_model import FamilyMember
from repositories.family_member_mappers import (
    family_member_to_domain,
    family_member_to_table,
)


class FamilyMemberRepository:
    """Repository para operaciones CRUD de miembros de la familia"""
    
    def __init__(self, session: Session, familia_id: int | None = None) -> None:
        self._session = session
        self._familia_id = familia_id

    def add(self, member: FamilyMember) -> Result[FamilyMember, DatabaseError]:
        """Agregar un nuevo miembro de la familia"""
        try:
            table_row = family_member_to_table(member)
            # Agregar familia_id si está configurado
            if self._familia_id is not None:
                table_row.familia_id = self._familia_id
            self._session.add(table_row)
            self._session.flush()

            created = family_member_to_domain(table_row)
            return Ok(created)
        except Exception as e:
            return Err(DatabaseError(message=f"Error al guardar miembro: {e}"))

    def get_all(self) -> Sequence[FamilyMember]:
        """Obtener todos los miembros de la familia"""
        query = self._session.query(FamilyMemberTable)
        if self._familia_id is not None:
            query = query.filter(FamilyMemberTable.familia_id == self._familia_id)
        rows = query.all()
        return [family_member_to_domain(row) for row in rows]

    def get_active(self) -> Sequence[FamilyMember]:
        """Obtener solo miembros activos de la familia"""
        query = self._session.query(FamilyMemberTable).filter(
            FamilyMemberTable.activo
        )
        if self._familia_id is not None:
            query = query.filter(FamilyMemberTable.familia_id == self._familia_id)
        rows = query.all()
        return [family_member_to_domain(row) for row in rows]

    def get_by_id(self, member_id: int) -> Result[FamilyMember, DatabaseError]:
        """Obtener un miembro por ID de la familia"""
        try:
            query = self._session.query(FamilyMemberTable).filter(
                FamilyMemberTable.id == member_id
            )
            if self._familia_id is not None:
                query = query.filter(FamilyMemberTable.familia_id == self._familia_id)
            row = query.first()
            
            if row is None:
                return Err(DatabaseError(message=f"Miembro {member_id} no encontrado"))
            
            return Ok(family_member_to_domain(row))
        except Exception as e:
            return Err(DatabaseError(message=f"Error al buscar miembro: {e}"))

    def update(self, member: FamilyMember) -> Result[FamilyMember, DatabaseError]:
        """Actualizar un miembro existente de la familia"""
        try:
            if member.id is None:
                return Err(DatabaseError(message="El miembro debe tener un ID"))
            
            query = self._session.query(FamilyMemberTable).filter(
                FamilyMemberTable.id == member.id
            )
            if self._familia_id is not None:
                query = query.filter(FamilyMemberTable.familia_id == self._familia_id)
            row = query.first()
            
            if row is None:
                return Err(DatabaseError(message=f"Miembro {member.id} no encontrado"))
            
            # Actualizar campos
            row.nombre = member.nombre
            row.tipo_miembro = member.tipo_miembro
            row.parentesco = member.parentesco
            row.especie = member.especie
            row.edad = member.edad
            row.estado_laboral = member.estado_laboral
            row.activo = member.activo
            row.notas = member.notas
            
            self._session.flush()
            return Ok(family_member_to_domain(row))
        except Exception as e:
            return Err(DatabaseError(message=f"Error al actualizar miembro: {e}"))

    def delete(self, member_id: int) -> Result[None, DatabaseError]:
        """Eliminar un miembro de la familia (soft delete - marcar como inactivo)"""
        try:
            query = self._session.query(FamilyMemberTable).filter(
                FamilyMemberTable.id == member_id
            )
            if self._familia_id is not None:
                query = query.filter(FamilyMemberTable.familia_id == self._familia_id)
            row = query.first()
            
            if row is None:
                return Err(DatabaseError(message=f"Miembro {member_id} no encontrado"))
            
            row.activo = False
            self._session.flush()
            return Ok(None)
        except Exception as e:
            return Err(DatabaseError(message=f"Error al eliminar miembro: {e}"))
