"""
Servicio Guardian para monitoreo y alertas de Contador Oriental AI
Monitorea la salud de los contenedores y envía alertas a Discord
"""

import asyncio
import logging
import os
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import (
    Any,
    Final,
    Literal,
    NamedTuple,
    Protocol,
    Self,
    TypeAlias,
    TypedDict,
)

import aiohttp
import docker
from docker.models.containers import Container

# ============================================================================
# CONFIGURACIÓN Y CONSTANTES
# ============================================================================

# Usar Final para constantes que no deben cambiar
DISCORD_WEBHOOK_URL: Final[str] = os.getenv(
    "DISCORD_WEBHOOK_URL",
    "https://discord.com/api/webhooks/1489405150425776169/MpA53Ap6AneB1ZoPfLO6NxEJaU-4iYvNoh8O5naKS1GnKSwaNme5W53l7_COy_DzeVcH",
)
CHECK_INTERVAL: Final[int] = int(os.getenv("CHECK_INTERVAL", "60"))

# Type alias para nombres de contenedores
ContainerName: TypeAlias = Literal["auditor_familiar_app", "auditor_familiar_db", "auditor_familiar_ocr_api"]
EXPECTED_CONTAINERS: Final[tuple[ContainerName, ...]] = ("auditor_familiar_app", "auditor_familiar_db", "auditor_familiar_ocr_api")

# Colores Discord como constantes tipadas
DiscordColor: TypeAlias = int
COLOR_RED: Final[DiscordColor] = 0xFF0000
COLOR_GREEN: Final[DiscordColor] = 0x00FF00
COLOR_BLUE: Final[DiscordColor] = 0x00AAFF
COLOR_YELLOW: Final[DiscordColor] = 0xFFA500

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger: Final[logging.Logger] = logging.getLogger(__name__)


# ============================================================================
# ENUMS Y ESTADOS
# ============================================================================

class ContainerState(Enum):
    """Estados posibles de un contenedor Docker."""
    RUNNING = auto()
    STOPPED = auto()
    PAUSED = auto()
    RESTARTING = auto()
    REMOVED = auto()
    UNKNOWN = auto()


class HealthStatus(Enum):
    """Estados de salud de un contenedor."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    NONE = "none"


# ============================================================================
# ESTRUCTURAS DE DATOS TIPADAS
# ============================================================================

@dataclass(frozen=True, slots=True)
class ContainerStatus:
    """
    Estado inmutable de un contenedor.
    
    frozen=True: Inmutable después de crear
    slots=True: Mejor performance en memoria
    """
    name: str
    is_healthy: bool
    state: ContainerState
    health_status: HealthStatus
    details: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __str__(self) -> str:
        status_emoji = "✅" if self.is_healthy else "❌"
        return f"{status_emoji} {self.name}: {self.state.name} ({self.health_status.value})"


@dataclass(frozen=True, slots=True)
class DiscordEmbed:
    """Estructura de un embed de Discord."""
    title: str
    description: str
    color: DiscordColor
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "color": self.color,
            "timestamp": self.timestamp.isoformat(),
        }


class DiscordPayload(TypedDict):
    """Payload tipado para webhook de Discord."""
    embeds: list[dict[str, Any]]


class ContainerCheckResult(NamedTuple):
    """Resultado de verificación de contenedor."""
    is_healthy: bool
    details: str
    state: ContainerState
    health: HealthStatus


# ============================================================================
# PROTOCOLOS (INTERFACES ABSTRACTAS)
# ============================================================================

class Notifier(Protocol):
    """Protocolo para notificadores."""
    
    async def send_alert(self, service: str, issue: str) -> None:
        """Envía alerta de problema."""
        ...
    
    async def send_recovery(self, service: str, message: str) -> None:
        """Envía notificación de recuperación."""
        ...
    
    async def send_message(self, title: str, description: str, color: DiscordColor) -> None:
        """Envía mensaje genérico."""
        ...


class Monitor(Protocol):
    """Protocolo para monitores."""
    
    async def check_all(self) -> dict[str, ContainerStatus]:
        """Verifica todos los contenedores y retorna estados."""
        ...
    
    def get_status(self, container_name: str) -> ContainerCheckResult:
        """Obtiene estado de un contenedor específico."""
        ...


# ============================================================================
# IMPLEMENTACIONES
# ============================================================================

class DiscordNotifier:
    """
    Notificador de Discord con tipado estricto.
    
    Implementa el protocolo Notifier.
    """
    
    HTTP_SUCCESS: Final[int] = 204
    
    def __init__(self, webhook_url: str) -> None:
        self._webhook_url: Final[str] = webhook_url
        self._session: aiohttp.ClientSession | None = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Lazy initialization de la sesión HTTP."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10),
                headers={"Content-Type": "application/json"},
            )
        return self._session
    
    async def close(self) -> None:
        """Cierra la sesión HTTP de forma segura."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        return self
    
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit."""
        await self.close()
    
    async def send_message(
        self,
        title: str,
        description: str,
        color: DiscordColor = COLOR_GREEN,
    ) -> None:
        """Envía mensaje embedido a Discord."""
        embed = DiscordEmbed(title=title, description=description, color=color)
        payload: DiscordPayload = {"embeds": [embed.to_dict()]}
        
        try:
            session = await self._get_session()
            async with session.post(self._webhook_url, json=payload) as response:
                if response.status == self.HTTP_SUCCESS:
                    logger.info("✅ Notificación enviada a Discord")
                else:
                    logger.error(f"❌ Error Discord: HTTP {response.status}")
        except aiohttp.ClientError as e:
            logger.error(f"❌ Error de conexión con Discord: {e}")
        except Exception as e:
            logger.exception(f"❌ Error inesperado enviando a Discord: {e}")
    
    async def send_alert(self, service: str, issue: str) -> None:
        """Envía alerta de problema."""
        await self.send_message(
            f"🚨 Alerta - {service}",
            f"**Problema detectado:** {issue}\n**Hora:** {datetime.now().strftime('%H:%M:%S')}",
            COLOR_RED,
        )
    
    async def send_recovery(self, service: str, message: str) -> None:
        """Envía notificación de recuperación."""
        await self.send_message(
            f"✅ Recuperado - {service}",
            f"**Servicio restaurado:** {message}\n**Hora:** {datetime.now().strftime('%H:%M:%S')}",
            COLOR_GREEN,
        )


class ContainerMonitor:
    """
    Monitor de contenedores Docker con tipado estricto.
    
    Implementa el protocolo Monitor.
    """
    
    def __init__(self, notifier: Notifier) -> None:
        self._notifier: Final[Notifier] = notifier
        self._docker: Final[docker.DockerClient] = docker.from_env()
        self._last_status: dict[str, bool] = {}
        self._lock: Final[asyncio.Lock] = asyncio.Lock()
    
    def _parse_container_state(self, container: Container) -> ContainerState:
        """Parsea el estado del contenedor a enum tipado."""
        status = container.status.lower()
        state_map: dict[str, ContainerState] = {
            "running": ContainerState.RUNNING,
            "exited": ContainerState.STOPPED,
            "paused": ContainerState.PAUSED,
            "restarting": ContainerState.RESTARTING,
        }
        return state_map.get(status, ContainerState.UNKNOWN)
    
    def _get_health_status(self, container: Container) -> HealthStatus:
        """Obtiene el estado de salud del contenedor."""
        try:
            health = container.attrs.get("State", {}).get("Health", {})
            if not health:
                return HealthStatus.NONE
            
            status = health.get("Status", "")
            health_map: dict[str, HealthStatus] = {
                "healthy": HealthStatus.HEALTHY,
                "unhealthy": HealthStatus.UNHEALTHY,
                "starting": HealthStatus.STARTING,
            }
            return health_map.get(status, HealthStatus.NONE)
        except Exception:
            return HealthStatus.NONE
    
    def get_status(self, container_name: str) -> ContainerCheckResult:
        """
        Obtiene estado detallado de un contenedor.
        
        Raises:
            docker.errors.NotFound: Si el contenedor no existe
            docker.errors.APIError: Si hay error de API de Docker
        """
        try:
            container: Container = self._docker.containers.get(container_name)
            state = self._parse_container_state(container)
            health = self._get_health_status(container)
            
            # Determinar si está saludable
            is_healthy = (
                state == ContainerState.RUNNING 
                and health in (HealthStatus.HEALTHY, HealthStatus.NONE)
            )
            
            details = f"State: {state.name}"
            if health != HealthStatus.NONE:
                details += f" | Health: {health.value}"
            
            return ContainerCheckResult(
                is_healthy=is_healthy,
                details=details,
                state=state,
                health=health,
            )
            
        except docker.errors.NotFound:
            return ContainerCheckResult(
                is_healthy=False,
                details="Container not found",
                state=ContainerState.REMOVED,
                health=HealthStatus.NONE,
            )
        except docker.errors.APIError as e:
            return ContainerCheckResult(
                is_healthy=False,
                details=f"Docker API error: {e}",
                state=ContainerState.UNKNOWN,
                health=HealthStatus.NONE,
            )
        except Exception as e:
            return ContainerCheckResult(
                is_healthy=False,
                details=f"Unexpected error: {e}",
                state=ContainerState.UNKNOWN,
                health=HealthStatus.NONE,
            )
    
    async def check_all(self) -> dict[str, ContainerStatus]:
        """
        Verifica todos los contenedores esperados.
        
        Thread-safe usando lock para evitar race conditions.
        """
        current_status: dict[str, ContainerStatus] = {}
        
        async with self._lock:
            for container_name in EXPECTED_CONTAINERS:
                result = self.get_status(container_name)
                
                status = ContainerStatus(
                    name=container_name,
                    is_healthy=result.is_healthy,
                    state=result.state,
                    health_status=result.health,
                    details=result.details,
                )
                current_status[container_name] = status
                
                # Verificar cambio de estado
                last_healthy = self._last_status.get(container_name, True)
                
                if last_healthy and not result.is_healthy:
                    await self._notifier.send_alert(
                        container_name,
                        f"El contenedor `{container_name}` ha dejado de funcionar.\n**Estado:** {result.details}",
                    )
                    logger.error(f"🚨 {status}")
                    
                elif not last_healthy and result.is_healthy:
                    await self._notifier.send_recovery(
                        container_name,
                        f"El contenedor `{container_name}` ha vuelto a la normalidad.",
                    )
                    logger.info(f"✅ {status}")
                
                # Log de debug para estado actual
                if result.is_healthy:
                    logger.debug(f"{status}")
            
            self._last_status = {
                name: status.is_healthy 
                for name, status in current_status.items()
            }
        
        return current_status
    
    def get_summary(self, statuses: dict[str, ContainerStatus]) -> str:
        """Genera resumen legible del estado de los contenedores."""
        unhealthy = [s for s in statuses.values() if not s.is_healthy]
        
        if unhealthy:
            names = ", ".join(s.name for s in unhealthy)
            return f"⚠️ Contenedores con problemas: {names}"
        
        return "✅ Todos los contenedores funcionando correctamente"


# ============================================================================
# SERVICIO PRINCIPAL
# ============================================================================

@dataclass
class GuardianConfig:
    """Configuración tipada del servicio Guardian."""
    webhook_url: str = DISCORD_WEBHOOK_URL
    check_interval: int = CHECK_INTERVAL
    expected_containers: tuple[ContainerName, ...] = EXPECTED_CONTAINERS
    
    def __post_init__(self) -> None:
        """Validación post-inicialización."""
        if self.check_interval < 10:
            raise ValueError("CHECK_INTERVAL debe ser al menos 10 segundos")


class GuardianService:
    """
    Servicio principal de Guardian con arquitectura moderna.
    
    Usa composition over inheritance y dependency injection.
    """
    
    def __init__(self, config: GuardianConfig | None = None) -> None:
        self._config: Final[GuardianConfig] = config or GuardianConfig()
        self._running: bool = False
        self._shutdown_event: asyncio.Event = asyncio.Event()
        
        # Inyección de dependencias
        self._notifier: DiscordNotifier | None = None
        self._monitor: ContainerMonitor | None = None
    
    async def __aenter__(self) -> Self:
        """Inicialización async del servicio."""
        self._notifier = DiscordNotifier(self._config.webhook_url)
        await self._notifier.__aenter__()
        self._monitor = ContainerMonitor(self._notifier)
        return self
    
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Limpieza async del servicio."""
        self._running = False
        self._shutdown_event.set()
        
        if self._notifier:
            await self._notifier.__aexit__(exc_type, exc_val, exc_tb)
    
    async def _send_startup_notification(self) -> None:
        """Envía notificación de inicio del servicio."""
        if not self._notifier:
            return
            
        containers_str = ", ".join(self._config.expected_containers)
        await self._notifier.send_message(
            "🛡️ Guardian Iniciado",
            f"**Servicio de monitoreo activo**\n"
            f"**Contenedores vigilados:** {containers_str}\n"
            f"**Intervalo:** {self._config.check_interval}s",
            COLOR_BLUE,
        )
    
    async def _monitoring_loop(self) -> None:
        """Loop principal de monitoreo."""
        if not self._monitor:
            raise RuntimeError("Monitor no inicializado")
        
        while self._running:
            try:
                statuses = await self._monitor.check_all()
                summary = self._monitor.get_summary(statuses)
                
                # Solo loggear warning si hay problemas
                if any(not s.is_healthy for s in statuses.values()):
                    logger.warning(summary)
                else:
                    logger.info(summary)
                
                # Esperar con cancelación graceful
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=self._config.check_interval,
                    )
                except asyncio.TimeoutError:
                    continue  # Normal, continuar con siguiente check
                    
            except asyncio.CancelledError:
                logger.info("🛡️ Loop de monitoreo cancelado")
                break
            except Exception as e:
                logger.exception(f"❌ Error en ciclo de monitoreo: {e}")
                await asyncio.sleep(10)
    
    async def start(self) -> None:
        """Inicia el servicio de monitoreo."""
        logger.info("🛡️ Iniciando Guardian Service...")
        await self._send_startup_notification()
        
        self._running = True
        self._shutdown_event.clear()
        
        try:
            await self._monitoring_loop()
        except KeyboardInterrupt:
            logger.info("🛡️ Señal de interrupción recibida")
        finally:
            self._running = False
    
    def stop(self) -> None:
        """Solicita detención del servicio de forma segura."""
        logger.info("🛡️ Solicitando detención de Guardian...")
        self._running = False
        self._shutdown_event.set()


# ============================================================================
# ENTRY POINT
# ============================================================================

async def main() -> int:
    """
    Función principal con manejo de señales y cleanup.
    
    Returns:
        Exit code (0 = success, 1 = error)
    """
    # Configurar manejo de señales para shutdown graceful
    loop = asyncio.get_running_loop()
    
    async with GuardianService() as guardian:
        # Manejar señales para shutdown graceful
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, guardian.stop)
        
        try:
            await guardian.start()
            return 0
        except Exception as e:
            logger.exception(f"❌ Error fatal: {e}")
            return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("🛡️ Programa terminado por usuario")
        sys.exit(0)
