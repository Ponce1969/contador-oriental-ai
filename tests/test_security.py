"""
Tests para core/security.py — RateLimiter y timeout de sesión.
No requiere BD ni Ollama.
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

from core.security import (
    RateLimiter,
    limpiar_sesion,
    registrar_actividad,
    sesion_expirada,
)


class TestRateLimiter:
    def setup_method(self):
        """Instancia fresca por cada test."""
        self.rl = RateLimiter(max_intentos=3, ventana_segundos=60, bloqueo_segundos=120)

    def test_sin_intentos_no_esta_bloqueado(self):
        bloqueado, seg = self.rl.esta_bloqueado("pepe")
        assert bloqueado is False
        assert seg == 0

    def test_usuario_desconocido_no_esta_bloqueado(self):
        bloqueado, _ = self.rl.esta_bloqueado("nadie")
        assert bloqueado is False

    def test_un_fallo_no_bloquea(self):
        bloqueado, seg = self.rl.registrar_fallo("pepe")
        assert bloqueado is False
        assert seg == 0

    def test_dos_fallos_no_bloquean(self):
        self.rl.registrar_fallo("pepe")
        bloqueado, _ = self.rl.registrar_fallo("pepe")
        assert bloqueado is False

    def test_tercer_fallo_bloquea(self):
        self.rl.registrar_fallo("pepe")
        self.rl.registrar_fallo("pepe")
        bloqueado, seg = self.rl.registrar_fallo("pepe")
        assert bloqueado is True
        assert seg > 0

    def test_esta_bloqueado_tras_tres_fallos(self):
        for _ in range(3):
            self.rl.registrar_fallo("pepe")
        bloqueado, seg = self.rl.esta_bloqueado("pepe")
        assert bloqueado is True
        assert seg > 100

    def test_exito_limpia_fallos(self):
        self.rl.registrar_fallo("pepe")
        self.rl.registrar_fallo("pepe")
        self.rl.registrar_exito("pepe")
        bloqueado, _ = self.rl.esta_bloqueado("pepe")
        assert bloqueado is False

    def test_exito_permite_nuevos_intentos(self):
        self.rl.registrar_fallo("pepe")
        self.rl.registrar_fallo("pepe")
        self.rl.registrar_exito("pepe")
        bloqueado, _ = self.rl.registrar_fallo("pepe")
        assert bloqueado is False

    def test_intentos_restantes_decrecen(self):
        assert self.rl.intentos_restantes("pepe") == 3
        self.rl.registrar_fallo("pepe")
        assert self.rl.intentos_restantes("pepe") == 2
        self.rl.registrar_fallo("pepe")
        assert self.rl.intentos_restantes("pepe") == 1

    def test_usuarios_independientes(self):
        for _ in range(3):
            self.rl.registrar_fallo("pepe")
        bloqueado_pepe, _ = self.rl.esta_bloqueado("pepe")
        bloqueado_juan, _ = self.rl.esta_bloqueado("juan")
        assert bloqueado_pepe is True
        assert bloqueado_juan is False

    def test_fallos_fuera_de_ventana_se_ignoran(self):
        rl = RateLimiter(max_intentos=3, ventana_segundos=1, bloqueo_segundos=60)
        rl.registrar_fallo("pepe")
        rl.registrar_fallo("pepe")
        time.sleep(1.1)
        bloqueado, _ = rl.registrar_fallo("pepe")
        assert bloqueado is False

    def test_bloqueo_expira_con_el_tiempo(self):
        rl = RateLimiter(max_intentos=2, ventana_segundos=60, bloqueo_segundos=1)
        rl.registrar_fallo("pepe")
        rl.registrar_fallo("pepe")
        bloqueado, _ = rl.esta_bloqueado("pepe")
        assert bloqueado is True
        time.sleep(1.1)
        bloqueado, _ = rl.esta_bloqueado("pepe")
        assert bloqueado is False

    def test_mensaje_incluye_minutos(self):
        rl = RateLimiter(max_intentos=1, ventana_segundos=60, bloqueo_segundos=120)
        rl.registrar_fallo("pepe")
        bloqueado, seg = rl.esta_bloqueado("pepe")
        assert bloqueado is True
        minutos = seg // 60 + 1
        assert minutos >= 1


class TestSessionTimeout:
    def test_sesion_nueva_no_expirada(self):
        registrar_actividad("session-abc")
        assert sesion_expirada("session-abc") is False

    def test_sesion_sin_actividad_no_expirada(self):
        assert sesion_expirada("session-nueva-sin-registrar") is False

    def test_sesion_expirada_por_inactividad(self):
        with patch("core.security.SESSION_TIMEOUT_SEGUNDOS", 0):
            registrar_actividad("session-vieja")
            time.sleep(0.01)
            assert sesion_expirada("session-vieja") is True

    def test_limpiar_sesion_elimina_timestamp(self):
        registrar_actividad("session-xyz")
        limpiar_sesion("session-xyz")
        assert sesion_expirada("session-xyz") is False

    def test_actividad_renueva_sesion(self):
        with patch("core.security.SESSION_TIMEOUT_SEGUNDOS", 1):
            registrar_actividad("session-activa")
            time.sleep(0.5)
            registrar_actividad("session-activa")
            time.sleep(0.6)
            assert sesion_expirada("session-activa") is False


class TestAuthServiceConSecurity:
    """Tests de integración AuthService + RateLimiter (mock de repo)."""

    def _make_service(self):
        from services.auth_service import AuthService
        repo = MagicMock()
        repo.get_by_username.return_value = MagicMock(
            is_err=lambda: True
        )
        return AuthService(repo)

    def test_bloqueo_tras_max_intentos(self):
        from models.user_model import UserLogin
        from result import Err

        svc = self._make_service()
        svc._ph = MagicMock()

        for _ in range(5):
            svc.login(UserLogin(username="atacante", password="wrongpass"))

        result = svc.login(UserLogin(username="atacante", password="wrongpass"))
        assert isinstance(result, Err)
        assert "minuto" in result.err_value.message.lower()

    def test_login_exitoso_limpia_fallos(self):
        from models.user_model import User, UserLogin
        from result import Ok

        from services.auth_service import AuthService

        user_mock = MagicMock(spec=User)
        user_mock.activo = True
        user_mock.id = 1
        user_mock.password_hash = "hash"

        repo = MagicMock()
        repo.get_by_username.return_value = MagicMock(
            is_err=lambda: False,
            ok_value=user_mock,
        )
        repo.update_last_login = MagicMock()

        svc = AuthService(repo)
        svc._verify_password = MagicMock(return_value=True)

        svc.login(UserLogin(username="usuario", password="password123"))
        svc.login(UserLogin(username="usuario", password="password123"))

        result = svc.login(UserLogin(username="usuario", password="password123"))
        assert isinstance(result, Ok)
