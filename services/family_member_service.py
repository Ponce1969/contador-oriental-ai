"""
Servicio de lógica de negocio para miembros de la familia
"""

from __future__ import annotations

from result import Err, Result

from constants.messages import ValidationMessages
from models.errors import DatabaseError, ValidationError
from models.family_member_model import FamilyMember
from repositories.family_member_repository import FamilyMemberRepository
from services.validators import validate_id_requerido


class FamilyMemberService:
    """Servicio para gestión de miembros de la familia con validaciones"""
    
    def __init__(self, repo: FamilyMemberRepository) -> None:
        self._repo = repo

    def create_member(
        self, member: FamilyMember
    ) -> Result[FamilyMember, ValidationError | DatabaseError]:
        """Crear un nuevo miembro con validaciones"""
        err = self._validate_member(member)
        if err is not None:
            return err
        return self._repo.add(member)

    def list_members(self) -> list[FamilyMember]:
        """Listar todos los miembros"""
        members = self._repo.get_all()
        return list(members)

    def list_active_members(self) -> list[FamilyMember]:
        """Listar solo miembros activos"""
        members = self._repo.get_active()
        return list(members)

    def get_member(self, member_id: int) -> Result[FamilyMember, DatabaseError]:
        """Obtener un miembro por ID"""
        return self._repo.get_by_id(member_id)

    def update_member(
        self, member: FamilyMember
    ) -> Result[FamilyMember, ValidationError | DatabaseError]:
        """Actualizar un miembro existente con validaciones"""
        id_check = validate_id_requerido(
            member.id, ValidationMessages.ID_REQUERIDO_MIEMBRO
        )
        if id_check.is_err():
            return id_check  # type: ignore[return-value]
        err = self._validate_member(member)
        if err is not None:
            return err
        return self._repo.update(member)

    def deactivate_member(self, member_id: int) -> Result[None, DatabaseError]:
        """Desactivar un miembro (soft delete)"""
        return self._repo.delete(member_id)

    def _validate_member(
        self, member: FamilyMember
    ) -> Result[FamilyMember, ValidationError] | None:
        """Validaciones comunes para create y update."""
        if not member.nombre or member.nombre.strip() == "":
            return Err(ValidationError(message=ValidationMessages.NOMBRE_REQUERIDO))
        if member.tipo_miembro not in ("persona", "mascota"):
            return Err(
                ValidationError(message=ValidationMessages.TIPO_MIEMBRO_INVALIDO)
            )
        if member.tipo_miembro == "persona" and not member.parentesco:
            return Err(ValidationError(message=ValidationMessages.PARENTESCO_REQUERIDO))
        if member.tipo_miembro == "mascota" and not member.especie:
            return Err(ValidationError(message=ValidationMessages.ESPECIE_REQUERIDA))
        return None
