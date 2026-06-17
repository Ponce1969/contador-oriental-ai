"""
Repositorio de tokens de reseteo de contraseña
"""

from datetime import datetime

from result import Err, Ok, Result
from sqlalchemy import text

from core.sqlalchemy_session import get_db_session
from models.errors import DatabaseError
from models.password_reset_model import PasswordResetToken


class PasswordResetRepository:
    """Repositorio para gestión de tokens de reseteo"""

    def __init__(self, session=None):
        self._session = session

    def _get_session(self):
        if self._session is not None:
            return self._session
        return get_db_session()

    def _use_session(self, callback):
        if self._session is not None:
            return callback(self._session)
        else:
            with get_db_session() as session:
                return callback(session)

    def create_token(
        self, user_id: int, token: str, expires_at: datetime
    ) -> Result[PasswordResetToken, DatabaseError]:
        """Crear un nuevo token de reseteo"""

        def _query(session):
            result = session.execute(
                text("""
                    INSERT INTO password_reset_tokens (user_id, token, expires_at)
                    VALUES (:user_id, :token, :expires_at)
                    RETURNING id, created_at
                """),
                {"user_id": user_id, "token": token, "expires_at": expires_at},
            )
            row = result.fetchone()
            if row is not None:
                return Ok(
                    PasswordResetToken(
                        id=row[0],
                        user_id=user_id,
                        token=token,
                        expires_at=expires_at,
                        created_at=row[1],
                    )
                )
            return Err(DatabaseError(message="Error al crear token de reseteo"))

        try:
            return self._use_session(_query)
        except Exception as e:
            return Err(DatabaseError(message="Error al crear token de reseteo"))

    def find_valid_token(
        self, token: str
    ) -> Result[PasswordResetToken | None, DatabaseError]:
        """Buscar token válido (no usado, no expirado)"""

        def _query(session):
            result = session.execute(
                text("""
                    SELECT id, user_id, token, expires_at, used_at, created_at
                    FROM password_reset_tokens
                    WHERE token = :token
                    AND used_at IS NULL
                    AND expires_at > CURRENT_TIMESTAMP
                """),
                {"token": token},
            )
            row = result.fetchone()
            if not row:
                return Ok(None)
            return Ok(
                PasswordResetToken(
                    id=row[0],
                    user_id=row[1],
                    token=row[2],
                    expires_at=row[3],
                    used_at=row[4],
                    created_at=row[5],
                )
            )

        try:
            return self._use_session(_query)
        except Exception as e:
            return Err(DatabaseError(message="Error al buscar token"))

    def claim_token(
        self, token: str
    ) -> Result[PasswordResetToken | None, DatabaseError]:
        """Atomically find and mark a token as used in a single operation.

        Uses UPDATE ... RETURNING to eliminate the TOCTOU race condition between
        find_valid_token (SELECT) and mark_used (UPDATE). If this returns a row,
        the caller owns the token — no concurrent request can claim it.
        If it returns None, the token was already used or expired.
        """

        def _query(session):
            result = session.execute(
                text("""
                    UPDATE password_reset_tokens
                    SET used_at = CURRENT_TIMESTAMP
                    WHERE token = :token
                    AND used_at IS NULL
                    AND expires_at > CURRENT_TIMESTAMP
                    RETURNING id, user_id, token, expires_at, used_at, created_at
                """),
                {"token": token},
            )
            row = result.fetchone()
            if not row:
                return Ok(None)
            session.commit()
            return Ok(
                PasswordResetToken(
                    id=row[0],
                    user_id=row[1],
                    token=row[2],
                    expires_at=row[3],
                    used_at=row[4],
                    created_at=row[5],
                )
            )

        try:
            return self._use_session(_query)
        except Exception as e:
            return Err(DatabaseError(message="Error al reclamar token"))

    def mark_used(self, token_id: int) -> Result[None, DatabaseError]:
        """Marcar token como usado"""

        def _query(session):
            session.execute(
                text("""
                    UPDATE password_reset_tokens
                    SET used_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                """),
                {"id": token_id},
            )
            return Ok(None)

        try:
            return self._use_session(_query)
        except Exception as e:
            return Err(
                DatabaseError(message="Error al marcar token como usado")
            )
