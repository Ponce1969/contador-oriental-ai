"""
Servicio de autenticación - Login, logout, gestión de usuarios
"""

from __future__ import annotations

import logging
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from result import Err, Ok, Result

from core.security import rate_limiter
from models.errors import AppError, DatabaseError, ValidationError
from models.user_model import User, UserCreate, UserLogin
from repositories.password_reset_repository import PasswordResetRepository
from repositories.user_repository import UserRepository

if TYPE_CHECKING:
    from services.infrastructure.email_service import EmailService

logger = logging.getLogger(__name__)


class AuthService:
    """Servicio de autenticación"""

    def __init__(self, user_repo: UserRepository):
        self._user_repo = user_repo
        self._reset_repo = PasswordResetRepository()
        self._ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)
        self._email_service: EmailService | None = None

    def set_email_service(self, email_service: EmailService) -> None:
        """Set email service (for dependency injection in tests)"""
        self._email_service = email_service

    def _get_email_service(self) -> EmailService:
        if self._email_service is None:
            from services.infrastructure.email_service import ResendEmailService

            self._email_service = ResendEmailService()
        return self._email_service

    def login(
        self, credentials: UserLogin
    ) -> Result[User, ValidationError | DatabaseError]:
        """
        Autenticar usuario con rate limiting.
        Retorna el usuario si las credenciales son correctas.
        """
        username = credentials.username

        # 1. Verificar si el usuario está bloqueado por demasiados fallos
        bloqueado, segundos = rate_limiter.esta_bloqueado(username)
        if bloqueado:
            minutos = segundos // 60 + 1
            return Err(
                ValidationError(
                    message=(
                        f"Demasiados intentos fallidos. "
                        f"Intentá de nuevo en {minutos} minuto(s)."
                    )
                )
            )

        # 2. Buscar usuario por username
        result = self._user_repo.get_by_username(username)
        if result.is_err():
            rate_limiter.registrar_fallo(username)
            return Err(ValidationError(message="Usuario o contraseña incorrectos"))

        user = result.ok_value

        # 3. Verificar que el usuario esté activo
        if not user.activo:
            return Err(ValidationError(message="Usuario inactivo"))

        # 4. Verificar contraseña
        if not self._verify_password(credentials.password, user.password_hash):
            bloqueado_ahora, seg_bloqueo = rate_limiter.registrar_fallo(username)
            if bloqueado_ahora:
                minutos = seg_bloqueo // 60 + 1
                return Err(
                    ValidationError(
                        message=(
                            f"Demasiados intentos fallidos. "
                            f"Cuenta bloqueada por {minutos} minuto(s)."
                        )
                    )
                )
            restantes = rate_limiter.intentos_restantes(username)
            return Err(
                ValidationError(
                    message=(
                        f"Usuario o contraseña incorrectos. "
                        f"Intentos restantes: {restantes}."
                    )
                )
            )

        # 5. Login exitoso — limpiar contador de fallos
        rate_limiter.registrar_exito(username)

        # 6. Actualizar último login
        if user.id is not None:
            self._user_repo.update_last_login(user.id)

        return Ok(user)

    def create_user(
        self, user_data: UserCreate
    ) -> Result[User, ValidationError | DatabaseError]:
        """Crear nuevo usuario con contraseña hasheada"""

        # Verificar que el username no exista
        existing = self._user_repo.get_by_username(user_data.username)
        if existing.is_ok():
            return Err(ValidationError(message="El nombre de usuario ya existe"))

        # Hashear contraseña
        password_hash = self._hash_password(user_data.password)

        # Crear usuario
        user = User(
            familia_id=user_data.familia_id,
            username=user_data.username,
            password_hash=password_hash,
            nombre_completo=user_data.nombre_completo,
            activo=True,
        )

        return self._user_repo.add(user)

    def change_password(
        self, user_id: int, old_password: str, new_password: str
    ) -> Result[None, ValidationError | DatabaseError]:
        """Cambiar contraseña de usuario"""

        # Obtener usuario
        result = self._user_repo.get_by_id(user_id)
        if result.is_err():
            return Err(ValidationError(message="Usuario no encontrado"))

        user = result.ok_value

        # Verificar contraseña actual
        if not self._verify_password(old_password, user.password_hash):
            return Err(ValidationError(message="Contraseña actual incorrecta"))

        # Validar nueva contraseña
        if len(new_password) < 6:
            return Err(
                ValidationError(
                    message="La contraseña debe tener al menos 6 caracteres"
                )
            )

        # Hashear nueva contraseña
        new_hash = self._hash_password(new_password)

        # Actualizar
        return self._user_repo.update_password(user_id, new_hash)

    def _hash_password(self, password: str) -> str:
        """Hashear contraseña con Argon2"""
        return self._ph.hash(password)

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verificar contraseña contra hash con Argon2"""
        try:
            self._ph.verify(password_hash, password)
            return True
        except VerifyMismatchError:
            return False
        except Exception:
            return False

    def request_password_reset(self, email: str) -> Result[str, AppError]:
        """
        Request password reset by email.
        Always returns success message (email enumeration protection).
        """
        # Rate limit: 3 requests per email per 15 minutes (using same limiter as login)
        bloqueado, segundos = rate_limiter.esta_bloqueado(f"reset_{email}")
        if bloqueado:
            minutos = segundos // 60 + 1
            # Still return generic message, but with rate limit info
            msg = (
                "Si tu email está registrado, recibirás un link para resetear tu "
                f"contraseña. Esperá {minutos} minuto(s) antes de intentar de nuevo."
            )
            return Ok(msg)

        # Try to find user by email
        user_result = self._user_repo.get_by_email(email.lower().strip())

        if user_result.is_ok():
            user = user_result.ok_value
            # Generate token
            token = secrets.token_urlsafe(32)
            expires_at = datetime.now(UTC) + timedelta(hours=1)

            # Store token
            token_result = self._reset_repo.create_token(
                user_id=user.id,
                token=token,
                expires_at=expires_at,
            )

            if token_result.is_ok():
                # Send email
                base_url = os.environ["APP_BASE_URL"]
                reset_url = f"{base_url}/reset-password?token={token}"

                email_result = self._get_email_service().send_password_reset(
                    email, reset_url
                )
                if email_result.is_err():
                    logger.error(
                        "Failed to send reset email to %s: %s",
                        email,
                        email_result.err_value,
                    )
            else:
                logger.error("Failed to create reset token: %s", token_result.err_value)

        # Register rate limit attempt
        rate_limiter.registrar_fallo(f"reset_{email}")

        # Always return generic message (email enumeration protection)
        msg = (
            "Si tu email está registrado, recibirás un link "
            "para resetear tu contraseña."
        )
        return Ok(msg)

    def reset_password(self, token: str, new_password: str) -> Result[None, AppError]:
        """Reset password using a valid token"""

        # Validate new password length
        if len(new_password) < 6:
            return Err(
                ValidationError(
                    message="La contraseña debe tener al menos 6 caracteres"
                )
            )

        # Find valid token
        token_result = self._reset_repo.find_valid_token(token)
        if token_result.is_err():
            return Err(AppError(message="Error al buscar token"))

        reset_token = token_result.ok_value
        if reset_token is None:
            return Err(
                ValidationError(message="Link inválido o expirado. Solicitá uno nuevo.")
            )

        # Update password
        new_hash = self._hash_password(new_password)
        password_result = self._user_repo.update_password(reset_token.user_id, new_hash)

        if password_result.is_err():
            return Err(AppError(message="Error al actualizar contraseña"))

        # Mark token as used
        self._reset_repo.mark_used(reset_token.id)

        # Register success in rate limiter (clear any reset rate limit)
        user_result = self._user_repo.get_by_id(reset_token.user_id)
        if user_result.is_ok():
            # Clear rate limit for this user
            rate_limiter.registrar_exito(f"reset_{user_result.ok_value.email}")

        return Ok(None)
