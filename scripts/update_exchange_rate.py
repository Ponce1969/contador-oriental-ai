#!/usr/bin/env python3
"""
update_exchange_rate.py  Actualización diaria de cotización USD/UYU
===============================================================
Consulta exchangerate-api.com y guarda el rate en PostgreSQL.
Ejecutar vía cron: 0 9 * * * cd /opt/contador-oriental && uv run python scripts/update_exchange_rate.py
"""
from __future__ import annotations

import asyncio
import os
import socket
import sys
from datetime import date
from pathlib import Path

# Agregar raíz del proyecto al path para imports
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

# Auto-detectar si estamos fuera de Docker: si no puede resolver 'postgres',
# fuerza POSTGRES_HOST=localhost para que funcione desde el host del servidor.
_default_host = os.getenv("POSTGRES_HOST", "postgres")
if _default_host == "postgres":
    try:
        socket.gethostbyname("postgres")
    except socket.gaierror:
        os.environ["POSTGRES_HOST"] = "localhost"

from core.sqlalchemy_session import get_db_session
from repositories.exchange_rate_repository import ExchangeRateRepository
from services.infrastructure.exchange_rate_service import ExchangeRateService


async def main() -> int:
    service = ExchangeRateService()
    result = await service.fetch_rate()

    if not result.ok:
        print(f"[ERROR] {result.err().message}")
        return 1

    rate = result.ok()
    today = date.today()

    with get_db_session() as session:
        repo = ExchangeRateRepository(session)
        existing = repo.get_today()
        if existing:
            print(f"[SKIP] Ya existe cotización para hoy ({today}): {existing.rate}")
            return 0

        saved = repo.save(rate, today)
        session.commit()
        print(f"[OK] Cotización guardada: {saved.currency_pair} = {saved.rate} ({saved.date})")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
