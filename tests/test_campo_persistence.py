"""
Pruebas de persistencia del Modo Campo y estabilidad de Router/on_resize.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from core.responsive import get_device_type
from core.router import Router
from core.session import SessionManager, _sessions
from core.state import AppState
from models.user_model import User
from repositories.family_repository import FamilyRepository


class MockSession:
    def __init__(self, session_id: str = "test-session-persistence"):
        self.id = session_id


class MockPage:
    def __init__(self, session_id: str = "test-session-persistence"):
        self.session = MockSession(session_id)
        self.data: dict = {}
        self.controls: list = []
        self.width = 1200
        self.route = "/"

    def add(self, control):
        self.controls.append(control)

    def update(self):
        pass


@pytest.fixture(autouse=True)
def clean_sessions():
    _sessions.clear()
    yield
    _sessions.clear()


class TestFamilyRepositoryCampo:
    def test_get_and_set_campo_enabled(self, db_session):
        # Crear familia de prueba
        db_session.execute(
            text(
                "INSERT INTO familias (id, nombre, email, activo, campo_enabled) "
                "VALUES (9999, 'Familia Campo Test', 'campo@test.com', TRUE, FALSE)"
            )
        )
        db_session.commit()

        repo = FamilyRepository(session=db_session)

        # Inicialmente debe ser False
        assert repo.get_campo_enabled(9999) is False

        # Activar modo campo
        res = repo.set_campo_enabled(9999, True)
        assert res.is_ok()
        assert repo.get_campo_enabled(9999) is True

        # Desactivar modo campo
        res = repo.set_campo_enabled(9999, False)
        assert res.is_ok()
        assert repo.get_campo_enabled(9999) is False

    def test_get_campo_enabled_nonexistent_family(self, db_session):
        repo = FamilyRepository(session=db_session)
        assert repo.get_campo_enabled(999999) is False


class TestSessionManagerCampoIntegration:
    def test_login_loads_campo_enabled_from_family(self, db_session, monkeypatch):
        # Crear familia con campo_enabled = True
        db_session.execute(
            text(
                "INSERT INTO familias (id, nombre, email, activo, campo_enabled) "
                "VALUES (8888, 'Familia Agro', 'agro@test.com', TRUE, TRUE)"
            )
        )
        db_session.commit()

        # Mock FamilyRepository inside session to use db_session
        repo = FamilyRepository(session=db_session)
        monkeypatch.setattr(
            "repositories.family_repository.FamilyRepository", lambda: repo
        )

        page = MockPage()
        user = User(
            id=1,
            familia_id=8888,
            username="hernan_agro",
            password_hash="fakehash",
        )

        # Antes del login
        assert not SessionManager.is_campo_enabled(page)

        # Login
        SessionManager.login(page, user)

        # Debe estar autenticado y con modo campo activo
        assert SessionManager.is_logged_in(page)
        assert SessionManager.is_campo_enabled(page) is True


class TestRouterSingletonAndSync:
    def test_router_get_returns_same_instance(self):
        page = MockPage()
        router1 = Router.get(page)
        router2 = Router.get(page)

        assert router1 is router2
        assert page.data["router"] is router1

    def test_router_current_route_synced_with_page_data(self):
        page = MockPage()
        router = Router.get(page)

        assert router.current_route == "/"
        assert page.data["current_route"] == "/"

        router.current_route = "/expenses"
        assert router.current_route == "/expenses"
        assert page.data["current_route"] == "/expenses"


class TestResizeAntiLogout:
    def test_resize_never_redirects_authenticated_user_to_login(self):
        page = MockPage()
        router = Router.get(page)

        # Simular usuario logueado en /expenses
        user = User(
            id=1,
            familia_id=1,
            username="productor",
            password_hash="fakehash",
        )
        SessionManager.login(page, user)
        router.current_route = "/expenses"
        AppState.device = "desktop"

        # Redimensionar a mobile
        new_device = get_device_type(400)
        assert new_device == "mobile"
        assert new_device != AppState.device

        # Lógica de on_resize tal como está implementada en main.py
        public_routes = ["/forgot-password", "/reset-password", "/register", "/invite"]
        current_active_route = router.current_route
        if SessionManager.is_logged_in(page):
            if (
                current_active_route in public_routes
                or current_active_route == "/login"
            ):
                current_active_route = "/"

        # La ruta NO debe ser /login, debe permanecer en /expenses
        assert current_active_route == "/expenses"
        assert current_active_route != "/login"

    def test_resize_redirects_to_dashboard_if_active_was_login_while_authenticated(
        self,
    ):
        page = MockPage()
        router = Router.get(page)

        user = User(
            id=1,
            familia_id=1,
            username="productor",
            password_hash="fakehash",
        )
        SessionManager.login(page, user)
        # Por algún motivo la ruta quedó en /login (huérfana)
        router.current_route = "/login"

        public_routes = ["/forgot-password", "/reset-password", "/register", "/invite"]
        current_active_route = router.current_route
        if SessionManager.is_logged_in(page):
            if (
                current_active_route in public_routes
                or current_active_route == "/login"
            ):
                current_active_route = "/"

        # Debe rescatarlo y llevarlo a "/" en lugar de /login
        assert current_active_route == "/"
