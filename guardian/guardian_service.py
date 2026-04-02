"""
Servicio Guardian para monitoreo y alertas de Contador Oriental AI
Monitorea la salud de los contenedores y envía alertas a Discord
"""

import asyncio
import logging
import os
import time
from datetime import datetime
from typing import Dict, List

import aiohttp
import docker
from docker.models.containers import Container

# Configuración
DISCORD_WEBHOOK_URL = os.getenv(
    "DISCORD_WEBHOOK_URL",
    "https://discord.com/api/webhooks/1489405150425776169/MpA53Ap6AneB1ZoPfLO6NxEJaU-4iYvNoh8O5naKS1GnKSwaNme5W53l7_COy_DzeVcH",
)
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))  # segundos
EXPECTED_CONTAINERS = ["app", "postgres", "ocr_api"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Envía notificaciones a Discord vía webhook"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send_message(self, title: str, description: str, color: int = 0x00FF00):
        """Envía mensaje embedido a Discord"""
        payload = {
            "embeds": [
                {
                    "title": title,
                    "description": description,
                    "color": color,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ]
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 204:
                        logger.info("✅ Notificación enviada a Discord")
                    else:
                        logger.error(f"❌ Error al enviar a Discord: {response.status}")
        except Exception as e:
            logger.error(f"❌ Error de conexión con Discord: {e}")

    async def send_alert(self, service: str, issue: str):
        """Envía alerta de problema"""
        await self.send_message(
            f"🚨 Alerta - {service}",
            f"**Problema detectado:** {issue}\n**Hora:** {datetime.now().strftime('%H:%M:%S')}",
            0xFF0000,  # Rojo
        )

    async def send_recovery(self, service: str, message: str):
        """Envía notificación de recuperación"""
        await self.send_message(
            f"✅ Recuperado - {service}",
            f"**Servicio restaurado:** {message}\n**Hora:** {datetime.now().strftime('%H:%M:%S')}",
            0x00FF00,  # Verde
        )


class ContainerMonitor:
    """Monitorea el estado de los contenedores Docker"""

    def __init__(self, discord: DiscordNotifier):
        self.discord = discord
        self.docker_client = docker.from_env()
        self.last_status: Dict[str, bool] = {}

    def get_container_status(self, container_name: str) -> tuple[bool, str]:
        """Verifica si un contenedor está saludable"""
        try:
            container = self.docker_client.containers.get(container_name)
            status = container.status.lower()

            if status == "running":
                # Verificar health check si existe
                health = container.attrs.get("State", {}).get("Health", {})
                if health:
                    health_status = health.get("Status", "")
                    return health_status == "healthy", f"Health: {health_status}"
                return True, "Running"
            else:
                return False, f"Status: {status}"

        except docker.errors.NotFound:
            return False, "Container not found"
        except Exception as e:
            return False, f"Error: {str(e)}"

    async def check_all_containers(self):
        """Verifica todos los contenedores esperados"""
        current_status = {}

        for container_name in EXPECTED_CONTAINERS:
            is_healthy, details = self.get_container_status(container_name)
            current_status[container_name] = is_healthy

            # Verificar cambio de estado
            last_healthy = self.last_status.get(container_name, True)

            if last_healthy and not is_healthy:
                # Se cayó
                await self.discord.send_alert(
                    container_name,
                    f"El contenedor `{container_name}` ha dejado de funcionar.\n**Estado:** {details}",
                )
                logger.error(f"🚨 Contenedor {container_name} caído: {details}")

            elif not last_healthy and is_healthy:
                # Se recuperó
                await self.discord.send_recovery(
                    container_name,
                    f"El contenedor `{container_name}` ha vuelto a la normalidad.",
                )
                logger.info(f"✅ Contenedor {container_name} recuperado")

        self.last_status = current_status

        # Reporte general
        unhealthy = [name for name, healthy in current_status.items() if not healthy]
        if unhealthy:
            logger.warning(f"⚠️ Contenedores con problemas: {', '.join(unhealthy)}")
        else:
            logger.info("✅ Todos los contenedores funcionando correctamente")

    async def send_startup_message(self):
        """Envía mensaje de inicio del servicio Guardian"""
        await self.discord.send_message(
            "🛡️ Guardian Iniciado",
            f"**Servicio de monitoreo activo**\n**Contenedores vigilados:** {', '.join(EXPECTED_CONTAINERS)}\n**Intervalo:** {CHECK_INTERVAL}s",
            0x00AAFF,  # Azul
        )


class GuardianService:
    """Servicio principal de Guardian"""

    def __init__(self):
        self.discord = DiscordNotifier(DISCORD_WEBHOOK_URL)
        self.monitor = ContainerMonitor(self.discord)
        self.running = False

    async def start(self):
        """Inicia el servicio de monitoreo"""
        logger.info("🛡️ Iniciando Guardian Service...")
        await self.monitor.send_startup_message()
        self.running = True

        while self.running:
            try:
                await self.monitor.check_all_containers()
                await asyncio.sleep(CHECK_INTERVAL)
            except KeyboardInterrupt:
                logger.info("🛡️ Guardian detenido por usuario")
                break
            except Exception as e:
                logger.error(f"❌ Error en ciclo de monitoreo: {e}")
                await asyncio.sleep(10)  # Esperar antes de reintentar

    def stop(self):
        """Detiene el servicio"""
        self.running = False


async def main():
    """Función principal"""
    guardian = GuardianService()

    try:
        await guardian.start()
    except KeyboardInterrupt:
        guardian.stop()
        logger.info("🛡️ Guardian service detenido")


if __name__ == "__main__":
    asyncio.run(main())
