"""
ExchangeRateScheduler — Actualización automática de cotización USD/UYU.

Se ejecuta al inicio de la app y cada 6 horas en background.
Si falla, loguea el error y reintenta en el próximo ciclo.
No bloquea la UI de Flet.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date

from core.sqlalchemy_session import get_db_session
from repositories.exchange_rate_repository import ExchangeRateRepository
from services.infrastructure.exchange_rate_service import ExchangeRateService
from services.infrastructure.formatters import format_cotizacion

logger = logging.getLogger(__name__)

# Intervalo entre actualizaciones (en segundos)
_UPDATE_INTERVAL = 6 * 60 * 60  # 6 horas


async def update_exchange_rate() -> None:
    """Consultar la API y guardar la cotización de hoy.

    Silenciosa: si ya existe, no hace nada. Si falla, loguea y continua.
    """
    try:
        service = ExchangeRateService()
        result = await service.fetch_rate()

        if not result.ok:
            logger.warning(
                "[EXCHANGE_RATE] Error consultando API: %s", result.err().message
            )
            return

        rate = result.ok()
        today = date.today()

        with get_db_session() as session:
            repo = ExchangeRateRepository(session)
            existing = repo.get_today()
            if existing:
                logger.info(
                    "[EXCHANGE_RATE] Cotización de hoy ya existe: %s", existing.rate
                )
                return

            repo.save(rate, today)
            session.commit()
            logger.info(
                "[EXCHANGE_RATE] Cotización actualizada: 1 USD = $ %s",
                format_cotizacion(rate),
            )

    except Exception as e:
        logger.error("[EXCHANGE_RATE] Error inesperado: %s", str(e))


async def exchange_rate_scheduler() -> None:
    """Task de background: actualiza al inicio y cada 6 horas."""
    # Primera actualización inmediata
    await update_exchange_rate()

    # Ciclo cada 6 horas
    while True:
        await asyncio.sleep(_UPDATE_INTERVAL)
        await update_exchange_rate()