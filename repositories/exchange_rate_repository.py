"""
Repositorio de cotizaciones de divisas
No filtra por familia: la cotización es global para todas las familias.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from database.tables import ExchangeRateTable
from models.exchange_rate_model import ExchangeRate


class ExchangeRateRepository:
    """Repositorio para cotizaciones USD/UYU"""

    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _to_domain(row: ExchangeRateTable) -> ExchangeRate:
        return ExchangeRate(
            id=row.id,
            currency_pair=row.currency_pair,
            rate=row.rate,
            date=row.date,
            created_at=row.created_at,
        )

    def get_today(self) -> ExchangeRate | None:
        """Retorna la cotización de hoy si existe."""
        row = (
            self.session.query(ExchangeRateTable)
            .filter(ExchangeRateTable.date == date.today())
            .first()
        )
        return self._to_domain(row) if row else None

    def get_latest(self) -> ExchangeRate | None:
        """Retorna la cotización más reciente (fallback si no hay de hoy)."""
        row = (
            self.session.query(ExchangeRateTable)
            .order_by(ExchangeRateTable.date.desc())
            .first()
        )
        return self._to_domain(row) if row else None

    def save(self, rate: Decimal, rate_date: date) -> ExchangeRate:
        """Guarda una nueva cotización. Si ya existe para esa fecha, la actualiza."""
        existing = (
            self.session.query(ExchangeRateTable)
            .filter(ExchangeRateTable.date == rate_date)
            .first()
        )
        if existing:
            existing.rate = rate
            self.session.flush()
            return self._to_domain(existing)

        table = ExchangeRateTable(
            rate=rate,
            date=rate_date,
            currency_pair="USD/UYU",
        )
        self.session.add(table)
        self.session.flush()
        return self._to_domain(table)
