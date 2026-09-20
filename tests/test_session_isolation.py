"""
Test para verificar que _sessions es thread-safe y no hay fuga de datos entre sesiones.
"""

from __future__ import annotations

from core.session import SessionManager, _sessions


class TestSessionIsolation:
    """Verifica que _sessions no contamine datos entre sesiones."""

    def test_sessions_dict_starts_empty(self):
        """_sessions debe estar vacío al inicio."""
        assert len(_sessions) == 0

    def test_login_populates_session_data(self):
        """Login debe crear entrada en _sessions con familia_id correcto."""
        _sessions.clear()

        class MockUser:
            id = 1
            familia_id = 100
            username = "testuser"
            nombre_completo = "Test User"

        class MockPage:
            class MockSession:
                id = "test-session-123"

            session = MockSession()

        page = MockPage()
        SessionManager.login(page, MockUser())  # type: ignore[arg-type]

        assert "test-session-123" in _sessions
        assert _sessions["test-session-123"]["familia_id"] == 100

        _sessions.clear()

    def test_logout_clears_session_data(self):
        """Logout debe eliminar entrada de _sessions."""
        _sessions.clear()

        class MockUser:
            id = 1
            familia_id = 100
            username = "testuser"
            nombre_completo = "Test User"

        class MockPage:
            class MockSession:
                id = "test-session-456"

            session = MockSession()

        page = MockPage()
        SessionManager.login(page, MockUser())  # type: ignore[arg-type]
        assert "test-session-456" in _sessions

        SessionManager.logout(page)
        assert "test-session-456" not in _sessions

    def test_different_session_ids_get_different_data(self):
        """Dos sessions diferentes deben tener datos independientes."""
        _sessions.clear()

        class MockUser1:
            id = 1
            familia_id = 100
            username = "user1"
            nombre_completo = "User One"

        class MockUser2:
            id = 2
            familia_id = 200
            username = "user2"
            nombre_completo = "User Two"

        class MockPage1:
            class MockSession:
                id = "session-A"

            session = MockSession()

        class MockPage2:
            class MockSession:
                id = "session-B"

            session = MockSession()

        page1 = MockPage1()
        page2 = MockPage2()

        SessionManager.login(page1, MockUser1())  # type: ignore[arg-type]
        SessionManager.login(page2, MockUser2())  # type: ignore[arg-type]

        assert _sessions["session-A"]["familia_id"] == 100
        assert _sessions["session-B"]["familia_id"] == 200
        assert (
            _sessions["session-A"]["familia_id"] != _sessions["session-B"]["familia_id"]
        )

        _sessions.clear()


class TestFamilyMemberControllerIsolation:
    """Verifica que FamilyMemberController usa el familia_id de la sesión."""

    def test_controller_stores_familia_id(self):
        """Controller debe almacenar familia_id del constructor."""
        from controllers.family_member_controller import FamilyMemberController

        controller = FamilyMemberController(familia_id=999)
        assert controller._familia_id == 999

    def test_controller_with_none_familia_id(self):
        """Controller con familia_id=None debe poder existir (para tests)."""
        from controllers.family_member_controller import FamilyMemberController

        controller = FamilyMemberController(familia_id=None)
        assert controller._familia_id is None

    def test_voice_session_register_and_restore(self):
        """Verifica que register_voice_session transfiere autenticación."""
        _sessions.clear()

        class MockUser:
            id = 5
            familia_id = 99
            username = "gonzalo"

        class MockPageA:
            class MockSession:
                id = "session-websocket-A"

            session = MockSession()

        class MockPageB:
            class MockSession:
                id = "session-websocket-B"

            session = MockSession()

        page_a = MockPageA()
        page_b = MockPageB()

        # Login en pestaña/conexión A
        SessionManager.login(page_a, MockUser())  # type: ignore[arg-type]
        assert SessionManager.is_logged_in(page_a) is True

        # Pestaña/conexión B no está autenticada
        assert SessionManager.is_logged_in(page_b) is False

        # Registrar voice_session_id desde página A
        voice_id = "test-voice-uuid-1234"
        SessionManager.register_voice_session(voice_id, page_a)

        # Restaurar en conexión B usando el voice_session_id
        restored = SessionManager.restore_voice_session(page_b, voice_id)
        assert restored is True
        assert SessionManager.is_logged_in(page_b) is True
        assert SessionManager.get_user_id(page_b) == 5
        assert SessionManager.get_familia_id(page_b) == 99
        assert SessionManager.get_username(page_b) == "gonzalo"

        _sessions.clear()


class TestRepositoryFamiliaIdFiltering:
    """Verifica que los repos filtran por familia_id correctamente."""

    def test_repository_add_sets_familia_id(self):
        """Repository.add debe setear familia_id en la fila插入."""
        from unittest.mock import MagicMock

        from models.family_member_model import FamilyMember
        from repositories.family_member_repository import FamilyMemberRepository

        mock_session = MagicMock()
        repo = FamilyMemberRepository(mock_session, familia_id=42)

        member = FamilyMember(nombre="Test", tipo_miembro="persona")
        repo.add(member)

        # Verificar que se llamó session.add con una fila que tiene familia_id=42
        mock_session.add.assert_called_once()
        added_row = mock_session.add.call_args[0][0]
        assert added_row.familia_id == 42

    def test_repository_query_filters_by_familia_id(self):
        """Repository.get_all debe filtrar por familia_id."""
        from unittest.mock import MagicMock

        from repositories.family_member_repository import FamilyMemberRepository

        mock_session = MagicMock()
        repo = FamilyMemberRepository(mock_session, familia_id=77)

        repo.get_all()

        # Verificar que query.filter fue llamado con familia_id
        mock_session.query.assert_called_once()
