"""
Sistema de sesión - Manejo de autenticación y estado del usuario
"""

import time

import flet as ft

from core.security import limpiar_sesion, registrar_actividad, sesion_expirada
from models.user_model import User

# Diccionario global para almacenar sesiones por session_id
_sessions: dict[str, dict] = {}

# TTL para sesiones abandonadas (sin logout explícito)
_SESSION_ABANDON_TTL = 8 * 3600  # 8 horas
_CREATED_AT = "_created_at"


def cleanup_expired_sessions() -> int:
    """Elimina sesiones abandonadas que excedieron el TTL. Retorna cuántas limpió."""
    now = time.time()
    expired = [
        sid
        for sid, data in _sessions.items()
        if now - data.get(_CREATED_AT, 0) > _SESSION_ABANDON_TTL
    ]
    for sid in expired:
        del _sessions[sid]
        limpiar_sesion(sid)
    return len(expired)


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
            _sessions[session_id] = {_CREATED_AT: time.time()}
        return _sessions[session_id]

    @staticmethod
    def login(page: ft.Page, user: User) -> None:
        """Iniciar sesión de usuario y registrar actividad inicial."""
        session_data = SessionManager._get_session_data(page)
        session_data[SessionManager.SESSION_KEY_USER_ID] = user.id
        session_data[SessionManager.SESSION_KEY_FAMILIA_ID] = user.familia_id
        session_data[SessionManager.SESSION_KEY_USERNAME] = user.username
        registrar_actividad(page.session.id)

        # Cargar preferencia de campo persistida en la familia
        try:
            from repositories.family_repository import FamilyRepository

            campo_enabled = FamilyRepository().get_campo_enabled(user.familia_id)
            SessionManager.set_campo_enabled(page, campo_enabled)
        except Exception:
            pass

    @staticmethod
    def logout(page: ft.Page) -> None:
        """Cerrar sesión y limpiar timestamp de actividad."""
        session_id = page.session.id

        # Invalidar cache de miembros antes de limpiar sesión
        from core.member_cache import member_cache

        session_data = SessionManager._get_session_data(page)
        familia_id = session_data.get(SessionManager.SESSION_KEY_FAMILIA_ID)
        if familia_id is not None:
            member_cache.invalidate(familia_id)

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

            router = Router.get(page)
            router.navigate("/login")
            return False

        return True

    @staticmethod
    def get_pending_invite(page: ft.Page) -> str | None:
        """Obtener token de invitación pendiente si existe"""
        session_data = SessionManager._get_session_data(page)
        return session_data.get("pending_invite_token")

    @staticmethod
    def set_pending_invite(page: ft.Page, token: str) -> None:
        """Guardar token de invitación pendiente"""
        session_data = SessionManager._get_session_data(page)
        session_data["pending_invite_token"] = token

    @staticmethod
    def clear_pending_invite(page: ft.Page) -> None:
        """Limpiar token de invitación pendiente"""
        session_data = SessionManager._get_session_data(page)
        if "pending_invite_token" in session_data:
            del session_data["pending_invite_token"]

    @staticmethod
    def is_campo_enabled(page: ft.Page) -> bool:
        """Indica si el módulo Campo/Rural está habilitado en la sesión"""
        session_data = SessionManager._get_session_data(page)
        return bool(session_data.get("campo_enabled", False))

    @staticmethod
    def set_campo_enabled(page: ft.Page, enabled: bool) -> None:
        """Habilitar o deshabilitar el módulo Campo/Rural"""
        session_data = SessionManager._get_session_data(page)
        session_data["campo_enabled"] = enabled
        from core.state import AppState

        AppState.campo_enabled = enabled
        if not enabled and SessionManager.get_active_entorno(page) == "campo":
            SessionManager.set_active_entorno(page, "hogar")

    @staticmethod
    def get_active_entorno(page: ft.Page) -> str:
        """Obtener el entorno activo: 'hogar' | 'campo' | 'consolidado'"""
        session_data = SessionManager._get_session_data(page)
        return session_data.get("active_entorno", "hogar")

    @staticmethod
    def set_active_entorno(page: ft.Page, entorno: str) -> None:
        """Definir el entorno activo"""
        session_data = SessionManager._get_session_data(page)
        session_data["active_entorno"] = entorno
        from core.state import AppState

        AppState.active_entorno = entorno

    @staticmethod
    def get_audited_period(page: ft.Page) -> tuple[int, int]:
        """Obtener año y mes del período en auditoría. Por defecto, mes actual."""
        session_data = SessionManager._get_session_data(page)
        period = session_data.get("audited_period")
        if period and isinstance(period, (tuple, list)) and len(period) == 2:
            return int(period[0]), int(period[1])
        from datetime import date

        today = date.today()
        return today.year, today.month

    @staticmethod
    def set_audited_period(page: ft.Page, year: int, month: int) -> None:
        """Establecer el período activo de auditoría en la sesión."""
        session_data = SessionManager._get_session_data(page)
        session_data["audited_period"] = (year, month)
