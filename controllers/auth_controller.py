"""
Controlador de autenticación - Manejo de login y usuarios
"""
import flet as ft
from result import Err, Ok, Result

from models.errors import AppError, DatabaseError, ValidationError
from models.user_model import User, UserLogin
from repositories.user_repository import UserRepository
from services.auth_service import AuthService


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
            return Err(
                AppError(message=f"Datos inválidos: {str(e)}")
            )
        
        result = self._auth_service.login(credentials)
        
        if result.is_err():
            error = result.err_value
            if isinstance(error, ValidationError):
                return Err(AppError(message=error.message))
            elif isinstance(error, DatabaseError):
                return Err(
                    AppError(message="Error de conexión. Intente nuevamente.")
                )
            else:
                return Err(AppError(message="Error desconocido"))
        
        return result
