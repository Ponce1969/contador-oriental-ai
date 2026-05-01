"""
Repositorio para tracking de uso de IA.
Controla cuotas diarias por familia para modelos cloud.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from database.tables import AiUsageTable
from models.ai_usage_model import AiUsage


class AiUsageRepository:
    """Repositorio para la tabla ai_usage."""

    def __init__(self, session: Session, familia_id: int) -> None:
        self.session = session
        self.familia_id = familia_id

    @staticmethod
    def _to_domain(row: AiUsageTable) -> AiUsage:
        return AiUsage(
            id=row.id,
            familia_id=row.familia_id,
            date=row.date,
            model=row.model,
            prompt_tokens=row.prompt_tokens,
            completion_tokens=row.completion_tokens,
            created_at=row.created_at,
        )

    def get_count_today(self, model: str = "llama3") -> int:
        """Retorna cuántas consultas hizo la familia hoy para un modelo."""
        result = (
            self.session.query(func.count(AiUsageTable.id))
            .filter(
                AiUsageTable.familia_id == self.familia_id,
                AiUsageTable.date == date.today(),
                AiUsageTable.model == model,
            )
            .scalar()
        )
        return result or 0

    def register_usage(
        self,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> AiUsage:
        """Registra una consulta. Upsert: si ya existe para hoy, suma tokens."""
        existing = (
            self.session.query(AiUsageTable)
            .filter(
                AiUsageTable.familia_id == self.familia_id,
                AiUsageTable.date == date.today(),
                AiUsageTable.model == model,
            )
            .first()
        )

        if existing:
            existing.prompt_tokens += prompt_tokens
            existing.completion_tokens += completion_tokens
            self.session.flush()
            return self._to_domain(existing)

        row = AiUsageTable(
            familia_id=self.familia_id,
            date=date.today(),
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        self.session.add(row)
        self.session.flush()
        return self._to_domain(row)

    def get_remaining_today(self, daily_limit: int, model: str = "llama3") -> int:
        """Retorna cuántas consultas quedan hoy para el modelo dado."""
        count = self.get_count_today(model)
        return max(0, daily_limit - count)