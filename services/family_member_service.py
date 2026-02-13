"""
Servicio de lógica de negocio para miembros de la familia
"""

from __future__ import annotations

from result import Err, Result

from models.errors import DatabaseError, ValidationError
from models.family_member_model import FamilyMember
from repositories.family_member_repository import FamilyMemberRepository


class FamilyMemberService:
    """Servicio para gestión de miembros de la familia con validaciones"""
    
    def __init__(self, repo: FamilyMemberRepository) -> None:
        self._repo = repo

    def create_member(
        self, member: FamilyMember
    ) -> Result[FamilyMember, ValidationError | DatabaseError]:
        """Crear un nuevo miembro con validaciones"""
        
        # Validación: nombre no puede estar vacío
        if not member.nombre or member.nombre.strip() == "":
            return Err(ValidationError(message="El nombre es obligatorio"))
        
        # Validación: tipo_miembro debe ser válido
        if member.tipo_miembro not in ("persona", "mascota"):
            return Err(ValidationError(message="Tipo de miembro inválido"))
        
        # Validación: personas deben tener parentesco
        if member.tipo_miembro == "persona" and not member.parentesco:
            return Err(ValidationError(message="Las personas deben tener parentesco"))
        
        # Validación: mascotas deben tener especie
        if member.tipo_miembro == "mascota" and not member.especie:
            return Err(ValidationError(message="Las mascotas deben tener especie"))
        
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
        
        # Validación: debe tener ID
        if member.id is None:
            return Err(ValidationError(message="El miembro debe tener un ID"))
        
        # Validación: nombre no puede estar vacío
        if not member.nombre or member.nombre.strip() == "":
            return Err(ValidationError(message="El nombre es obligatorio"))
        
        # Validación: tipo_miembro debe ser válido
        if member.tipo_miembro not in ("persona", "mascota"):
            return Err(ValidationError(message="Tipo de miembro inválido"))
        
        # Validación: personas deben tener parentesco
        if member.tipo_miembro == "persona" and not member.parentesco:
            return Err(ValidationError(message="Las personas deben tener parentesco"))
        
        # Validación: mascotas deben tener especie
        if member.tipo_miembro == "mascota" and not member.especie:
            return Err(ValidationError(message="Las mascotas deben tener especie"))
        
        return self._repo.update(member)

    def deactivate_member(self, member_id: int) -> Result[None, DatabaseError]:
        """Desactivar un miembro (soft delete)"""
        return self._repo.delete(member_id)
