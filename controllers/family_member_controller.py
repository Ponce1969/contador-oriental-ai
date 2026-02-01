"""
Controller para gestión de miembros de la familia
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from result import Result
from sqlalchemy.orm import Session

from core.sqlalchemy_session import get_db_session
from models.errors import AppError
from models.family_member_model import FamilyMember
from repositories.family_member_repository import FamilyMemberRepository
from services.family_member_service import FamilyMemberService


class FamilyMemberController:
    """Controller para gestión de miembros de la familia"""

    def __init__(
        self,
        session: Session | None = None,
        familia_id: int | None = None,
    ) -> None:
        self._session = session
        self._familia_id = familia_id

    @contextmanager
    def _get_session(self) -> Generator[Session, None, None]:
        """Obtener sesión de base de datos."""
        if self._session:
            yield self._session
        else:
            with get_db_session() as session:
                yield session

    def get_title(self) -> str:
        return "Miembros de la Familia"

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
