"""
Seguridad de autenticación:
- Rate limiting por username (max intentos fallidos en ventana de tiempo)
- Bloqueo temporal de usuario tras N fallos consecutivos
- Timeout de sesión inactiva
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuración (sobreescribible por variables de entorno)
# ---------------------------------------------------------------------------
MAX_INTENTOS = int(os.getenv("AUTH_MAX_INTENTOS", "5"))
VENTANA_SEGUNDOS = int(os.getenv("AUTH_VENTANA_SEGUNDOS", "900"))   # 15 min
BLOQUEO_SEGUNDOS = int(os.getenv("AUTH_BLOQUEO_SEGUNDOS", "900"))   # 15 min
SESSION_TIMEOUT_SEGUNDOS = int(os.getenv("SESSION_TIMEOUT_SEGUNDOS", "28800"))  # 8 h


# ---------------------------------------------------------------------------
# Rate limiter en memoria (singleton de proceso)
# ---------------------------------------------------------------------------
@dataclass
class _EntradaIntento:
    timestamps: list[float] = field(default_factory=list)
    bloqueado_hasta: float = 0.0


class RateLimiter:
    """
    Limita intentos de login por username.
    Thread-safe — usa un Lock interno.
    Almacenamiento en memoria: se resetea al reiniciar la app.
    """

    def __init__(
        self,
        max_intentos: int = MAX_INTENTOS,
        ventana_segundos: int = VENTANA_SEGUNDOS,
        bloqueo_segundos: int = BLOQUEO_SEGUNDOS,
    ) -> None:
        self._max_intentos = max_intentos
        self._ventana = ventana_segundos
        self._bloqueo = bloqueo_segundos
        self._entradas: dict[str, _EntradaIntento] = {}
        self._lock = Lock()

    def _limpiar_timestamps(self, entrada: _EntradaIntento, ahora: float) -> None:
        """Elimina timestamps fuera de la ventana de tiempo."""
        ventana_inicio = ahora - self._ventana
        entrada.timestamps = [t for t in entrada.timestamps if t > ventana_inicio]

    def esta_bloqueado(self, username: str) -> tuple[bool, int]:
        """
        Retorna (bloqueado, segundos_restantes).
        Si no está bloqueado: (False, 0).
        """
        with self._lock:
            ahora = time.time()
            entrada = self._entradas.get(username)
            if not entrada:
                return False, 0
            if entrada.bloqueado_hasta > ahora:
                restantes = int(entrada.bloqueado_hasta - ahora)
                return True, restantes
            return False, 0

    def registrar_fallo(self, username: str) -> tuple[bool, int]:
        """
        Registra un intento fallido.
        Retorna (ahora_bloqueado, segundos_de_bloqueo).
        """
        with self._lock:
            ahora = time.time()
            if username not in self._entradas:
                self._entradas[username] = _EntradaIntento()

            entrada = self._entradas[username]
            self._limpiar_timestamps(entrada, ahora)
            entrada.timestamps.append(ahora)

            if len(entrada.timestamps) >= self._max_intentos:
                entrada.bloqueado_hasta = ahora + self._bloqueo
                entrada.timestamps.clear()
                logger.warning(
                    "[SECURITY] Usuario '%s' bloqueado por %ds tras %d fallos",
                    username,
                    self._bloqueo,
                    self._max_intentos,
                )
                return True, self._bloqueo

            restantes = self._max_intentos - len(entrada.timestamps)
            logger.info(
                "[SECURITY] Fallo de login '%s'. Intentos restantes: %d",
                username,
                restantes,
            )
            return False, 0

    def registrar_exito(self, username: str) -> None:
        """Limpia el historial de fallos tras login exitoso."""
        with self._lock:
            self._entradas.pop(username, None)
            logger.info("[SECURITY] Login exitoso '%s'. Contador reseteado.", username)

    def intentos_restantes(self, username: str) -> int:
        """Cuántos intentos le quedan antes del bloqueo."""
        with self._lock:
            ahora = time.time()
            entrada = self._entradas.get(username)
            if not entrada:
                return self._max_intentos
            self._limpiar_timestamps(entrada, ahora)
            return max(0, self._max_intentos - len(entrada.timestamps))


# Singleton global del proceso
rate_limiter = RateLimiter()


# ---------------------------------------------------------------------------
# Timeout de sesión
# ---------------------------------------------------------------------------
_session_timestamps: dict[str, float] = {}
_session_lock = Lock()


def registrar_actividad(session_id: str) -> None:
    """Actualiza el timestamp de última actividad de una sesión."""
    with _session_lock:
        _session_timestamps[session_id] = time.time()


def sesion_expirada(session_id: str) -> bool:
    """
    Retorna True si la sesión superó SESSION_TIMEOUT_SEGUNDOS de inactividad.
    Una sesión nueva (sin timestamp) no se considera expirada.
    """
    with _session_lock:
        ultima = _session_timestamps.get(session_id)
        if ultima is None:
            return False
        return (time.time() - ultima) > SESSION_TIMEOUT_SEGUNDOS


def limpiar_sesion(session_id: str) -> None:
    """Elimina el timestamp de sesión al hacer logout."""
    with _session_lock:
        _session_timestamps.pop(session_id, None)
