"""
Sistema de eventos Observer para el Contador Oriental.
Desacopla controladores de servicios de IA: el controller solo emite,
la IA escucha en background sin bloquear la UI.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class EventType(Enum):
    GASTO_CREADO = "gasto_creado"
    INGRESO_CREADO = "ingreso_creado"
    SNAPSHOT_CREADO = "snapshot_creado"
    OCR_PROCESADO = "ocr_procesado"


@dataclass
class Event:
    """Evento del sistema con tipado estricto"""
    type: EventType
    familia_id: int
    data: dict[str, Any]
    source_id: int | None = None
    timestamp: str | None = None


AsyncHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventSystem:
    """
    Sistema de eventos async con patrón Observer.
    Los handlers se ejecutan en background sin bloquear la UI de Flet.
    """

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[AsyncHandler]] = {}

    def subscribe(self, event_type: EventType, handler: AsyncHandler) -> None:
        """Suscribir un handler async a un tipo de evento."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(
            "Handler suscrito a '%s': %s", event_type.value, handler.__qualname__
        )

    async def publish(self, event: Event) -> None:
        """
        Publicar evento a todos los handlers suscriptos.
        Los ejecuta en paralelo con gather; los errores no rompen el flujo principal.
        """
        handlers = self._handlers.get(event.type, [])
        if not handlers:
            return

        tasks = [
            asyncio.create_task(_safe_handle(handler, event))
            for handler in handlers
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    def fire_and_forget(self, event: Event) -> None:
        """
        Publicar evento sin await (fire-and-forget seguro).
        Usar en contextos síncronos o cuando no se quiere esperar.
        """
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_publish_safe(self, event))
        except RuntimeError:
            logger.warning(
                "[EVENT_SYSTEM] No hay event loop activo para publicar '%s'",
                event.type.value,
            )

    def clear(self) -> None:
        """Limpiar todos los handlers (útil en tests)."""
        self._handlers.clear()


async def _safe_handle(handler: AsyncHandler, event: Event) -> None:
    """Ejecutar handler con logging de errores estructurado."""
    try:
        await handler(event)
    except Exception as e:
        logger.error(
            "[MEMORY_EVENT_FAILED] familia_id=%s event_type=%s handler=%s error=%s",
            event.familia_id,
            event.type.value,
            handler.__qualname__,
            str(e),
        )


async def _publish_safe(system: EventSystem, event: Event) -> None:
    """Wrapper async para fire_and_forget."""
    await system.publish(event)


event_system = EventSystem()
