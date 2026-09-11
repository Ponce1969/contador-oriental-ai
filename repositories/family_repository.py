"""
Repositorio de familias - Gestión de configuración y datos a nivel familia
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from result import Err, Ok, Result
from sqlalchemy import text

from core.sqlalchemy_session import get_db_session
from models.errors import DatabaseError

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class FamilyRepository:
    """Repositorio para la entidad familias."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def _use_session(self, callback):
        if self._session is not None:
            return callback(self._session)
        with get_db_session() as session:
            return callback(session)

    def get_campo_enabled(self, familia_id: int) -> bool:
        """Obtener si el modo campo está habilitado para la familia."""

        def _query(session):
            result = session.execute(
                text("SELECT campo_enabled FROM familias WHERE id = :fid"),
                {"fid": familia_id},
            ).fetchone()
            if result is not None and result[0] is not None:
                return bool(result[0])
            return False

        try:
            return self._use_session(_query)
        except Exception:
            return False

    def set_campo_enabled(
        self, familia_id: int, enabled: bool
    ) -> Result[bool, DatabaseError]:
        """Actualizar el estado del modo campo para la familia."""

        def _query(session):
            session.execute(
                text("UPDATE familias SET campo_enabled = :enabled WHERE id = :fid"),
                {"fid": familia_id, "enabled": enabled},
            )
            session.commit()
            return Ok(True)

        try:
            return self._use_session(_query)
        except Exception as e:
            return Err(
                DatabaseError(
                    message=f"Error al actualizar configuración de campo: {e}"
                )
            )
