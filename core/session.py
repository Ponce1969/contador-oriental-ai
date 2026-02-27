"""
Sistema de sesión - Manejo de autenticación y estado del usuario
"""
import flet as ft

from core.security import limpiar_sesion, registrar_actividad, sesion_expirada
from models.user_model import User

# Diccionario global para almacenar sesiones por session_id
_sessions = {}


class SessionManager:
    """Gestor de sesión de usuario"""
    
    SESSION_KEY_USER_ID = "user_id"
    SESSION_KEY_FAMILIA_ID = "familia_id"
    SESSION_KEY_USERNAME = "username"
    
    @staticmethod
    def _get_session_data(page: ft.Page) -> dict:
        """Obtener o crear datos de sesión para esta página"""
        session_id = page.session.id
        if session_id not in _sessions:
            _sessions[session_id] = {}
        return _sessions[session_id]
    
    @staticmethod
    def login(page: ft.Page, user: User) -> None:
        """Iniciar sesión de usuario y registrar actividad inicial."""
        session_data = SessionManager._get_session_data(page)
        session_data[SessionManager.SESSION_KEY_USER_ID] = user.id
        session_data[SessionManager.SESSION_KEY_FAMILIA_ID] = user.familia_id
        session_data[SessionManager.SESSION_KEY_USERNAME] = user.username
        registrar_actividad(page.session.id)

    @staticmethod
    def logout(page: ft.Page) -> None:
        """Cerrar sesión y limpiar timestamp de actividad."""
        session_id = page.session.id
        if session_id in _sessions:
            del _sessions[session_id]
        limpiar_sesion(session_id)

    @staticmethod
    def is_logged_in(page: ft.Page) -> bool:
        """
        Verificar si hay sesión activa y no expirada por inactividad.
        Si expiró, limpia la sesión automáticamente.
        """
        session_id = page.session.id
        session_data = SessionManager._get_session_data(page)
        if SessionManager.SESSION_KEY_USER_ID not in session_data:
            return False
        if sesion_expirada(session_id):
            SessionManager.logout(page)
            return False
        registrar_actividad(session_id)
        return True
    
    @staticmethod
    def get_user_id(page: ft.Page) -> int | None:
        """Obtener ID del usuario actual"""
        session_data = SessionManager._get_session_data(page)
        return session_data.get(SessionManager.SESSION_KEY_USER_ID)
    
    @staticmethod
    def get_familia_id(page: ft.Page) -> int | None:
        """Obtener ID de la familia del usuario actual"""
        session_data = SessionManager._get_session_data(page)
        return session_data.get(SessionManager.SESSION_KEY_FAMILIA_ID)
    
    @staticmethod
    def get_username(page: ft.Page) -> str | None:
        """Obtener username del usuario actual"""
        session_data = SessionManager._get_session_data(page)
        return session_data.get(SessionManager.SESSION_KEY_USERNAME)
    
    @staticmethod
    def require_login(page: ft.Page) -> bool:
        """
        Verificar login y redirigir si no está autenticado o sesión expiró.
        Retorna True si está logueado, False si no.
        """
        if not SessionManager.is_logged_in(page):
            from core.router import Router
            router = Router(page)
            router.navigate("/login")
            return False
        return True
