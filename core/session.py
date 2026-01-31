"""
Sistema de sesión - Manejo de autenticación y estado del usuario
"""
import flet as ft

from models.user_model import User


class SessionManager:
    """Gestor de sesión de usuario"""
    
    SESSION_KEY_USER_ID = "user_id"
    SESSION_KEY_FAMILIA_ID = "familia_id"
    SESSION_KEY_USERNAME = "username"
    
    @staticmethod
    def login(page: ft.Page, user: User) -> None:
        """Iniciar sesión de usuario"""
        page.session.set(SessionManager.SESSION_KEY_USER_ID, user.id)
        page.session.set(SessionManager.SESSION_KEY_FAMILIA_ID, user.familia_id)
        page.session.set(SessionManager.SESSION_KEY_USERNAME, user.username)
    
    @staticmethod
    def logout(page: ft.Page) -> None:
        """Cerrar sesión"""
        page.session.clear()
    
    @staticmethod
    def is_logged_in(page: ft.Page) -> bool:
        """Verificar si hay sesión activa"""
        return page.session.contains_key(SessionManager.SESSION_KEY_USER_ID)
    
    @staticmethod
    def get_user_id(page: ft.Page) -> int | None:
        """Obtener ID del usuario actual"""
        return page.session.get(SessionManager.SESSION_KEY_USER_ID)
    
    @staticmethod
    def get_familia_id(page: ft.Page) -> int | None:
        """Obtener ID de la familia del usuario actual"""
        return page.session.get(SessionManager.SESSION_KEY_FAMILIA_ID)
    
    @staticmethod
    def get_username(page: ft.Page) -> str | None:
        """Obtener username del usuario actual"""
        return page.session.get(SessionManager.SESSION_KEY_USERNAME)
    
    @staticmethod
    def require_login(page: ft.Page) -> bool:
        """
        Verificar login y redirigir si no está autenticado
        Retorna True si está logueado, False si no
        """
        if not SessionManager.is_logged_in(page):
            from core.router import Router
            router = Router(page)
            router.navigate("/login")
            return False
        return True
