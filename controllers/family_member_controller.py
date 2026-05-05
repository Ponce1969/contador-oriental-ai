"""
Controller para gestión de miembros de la familia
"""

from __future__ import annotations

from result import Result

from controllers.base_controller import BaseController
from core.unit_of_work import UnitOfWork
from models.errors import AppError
from models.family_member_model import FamilyMember
from repositories.family_member_repository import FamilyMemberRepository
from services.domain.family_member_service import FamilyMemberService


class FamilyMemberController(BaseController):
    """
    Controller para gestión de miembros de la familia.
    Soporta UoW inyectado para transacciones atómicas.
    """

    def __init__(
        self,
        familia_id: int | None = None,
        uow: UnitOfWork | None = None,
    ) -> None:
        super().__init__(familia_id=familia_id, uow=uow)

    def add_member(self, member: FamilyMember) -> Result[FamilyMember, AppError]:
        """Agregar un nuevo miembro"""
        with self._get_session() as session:
            repo = FamilyMemberRepository(session, self._familia_id)
            service = FamilyMemberService(repo)
            return service.create_member(member)

    def list_members(self) -> list[FamilyMember]:
        """Listar todos los miembros"""
        with self._get_session() as session:
            repo = FamilyMemberRepository(session, self._familia_id)
            service = FamilyMemberService(repo)
            return service.list_members()

    def list_active_members(self) -> list[FamilyMember]:
        """Listar solo miembros activos"""
        with self._get_session() as session:
            repo = FamilyMemberRepository(session, self._familia_id)
            service = FamilyMemberService(repo)
            return service.list_active_members()

    def update_member(self, member: FamilyMember) -> Result[FamilyMember, AppError]:
        """Actualizar un miembro existente"""
        with self._get_session() as session:
            repo = FamilyMemberRepository(session, self._familia_id)
            service = FamilyMemberService(repo)
            return service.update_member(member)

    def deactivate_member(self, member_id: int) -> Result[None, AppError]:
        """Desactivar un miembro"""
        with self._get_session() as session:
            repo = FamilyMemberRepository(session, self._familia_id)
            service = FamilyMemberService(repo)
            return service.deactivate_member(member_id)
