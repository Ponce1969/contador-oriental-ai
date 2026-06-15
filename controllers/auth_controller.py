"""
Controlador de autenticación - Manejo de login y usuarios
"""

import flet as ft
from result import Err, Ok, Result

from models.errors import AppError, DatabaseError, ValidationError
from models.user_model import User, UserLogin
from repositories.user_repository import UserRepository
from services.domain.auth_service import AuthService


class AuthController:
    """Controlador de autenticación"""

    def __init__(self, page: ft.Page):
        self.page = page
        self._user_repo = UserRepository()
        self._auth_service = AuthService(self._user_repo)

    def login(self, username: str, password: str) -> Result[User, AppError]:
        """
        Intentar login de usuario
        Retorna el usuario si es exitoso
        """
        try:
            credentials = UserLogin(username=username, password=password)
        except Exception as e:
            return Err(AppError(message=f"Datos inválidos: {str(e)}"))

        result = self._auth_service.login(credentials)

        if result.is_err():
            error = result.err_value
            if isinstance(error, ValidationError):
                return Err(AppError(message=error.message))
            elif isinstance(error, DatabaseError):
                return Err(AppError(message="Error de conexión. Intente nuevamente."))
            else:
                return Err(AppError(message="Error desconocido"))

        return result

    def request_password_reset(self, email: str) -> Result[str, AppError]:
        """Request password reset by email"""
        if not email or "@" not in email:
            return Err(AppError(message="Ingresá un email válido"))

        return self._auth_service.request_password_reset(email.lower().strip())

    def reset_password(self, token: str, new_password: str) -> Result[None, AppError]:
        """Reset password using token"""
        return self._auth_service.reset_password(token, new_password)

    def update_email(self, user_id: int, email: str | None) -> Result[str, AppError]:
        """Update email for current user. None removes the email."""
        if email is not None:
            email = email.lower().strip()
            if email and "@" not in email:
                return Err(AppError(message="Ingresá un email válido"))

        email_value = email if email else None
        result = self._user_repo.update_email(user_id, email_value)

        if result.is_ok():
            if email_value:
                return Ok("Email actualizado correctamente")
            return Ok("Email eliminado")
        else:
            error = result.err_value
            return Err(AppError(message=error.message))
