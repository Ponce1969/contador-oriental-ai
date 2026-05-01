"""
Controller para cotización de divisas
Provee a la UI el valor del día con lógica de fallback.
"""
from __future__ import annotations

from decimal import Decimal

from core.sqlalchemy_session import get_db_session
from repositories.exchange_rate_repository import ExchangeRateRepository


class ExchangeRateController:
    """Controller para acceder a la cotización USD/UYU"""

    def get_display_rate(self) -> tuple[Decimal, bool]:
        """
        Retorna (rate, es_fresh).

        es_fresh=True  → cotización de hoy.
        es_fresh=False → fallback (día anterior o más viejo).

        Si no hay datos en la DB, retorna (Decimal("0"), False).
        """
        with get_db_session() as session:
            repo = ExchangeRateRepository(session)

            today = repo.get_today()
            if today:
                return today.rate, True

            latest = repo.get_latest()
            if latest:
                return latest.rate, False

        return Decimal("0"), False
