"""
QuotaManager — Control de cuotas diarias para modelos cloud de IA.
Regula el uso de Llama 3 70B por familia con límite configurable.
Si la cuota se agota, cae automáticamente a Gemma 2:2b con aviso.
"""
from __future__ import annotations

import logging
import os
from datetime import date

from sqlalchemy.orm import Session

from models.ai_usage_model import AiUsage
from repositories.ai_usage_repository import AiUsageRepository

logger = logging.getLogger(__name__)

# Límite diario por familia (editable via env var)
DEFAULT_DAILY_LIMIT = 10

MENSAJE_CUOTA_AGOTADA = (
    "⚠️ Respuesta con precisión reducida. "
    "La cuota diaria de consultas avanzadas está agotada. "
    "Se renueva a medianoche."
)


class QuotaManager:
    """
    Control de cuotas diarias para modelos cloud de IA.

    Reglas:
    - Cada familia tiene N consultas diarias de Llama 3.
    - Gemma 2 es local y no tiene límite.
    - Si la cuota se agota, se cae a Gemma 2 con aviso al usuario.
    - El límite es configurable via LLAMA3_DAILY_QUOTA en .env.
    """

    def __init__(self, session: Session, familia_id: int) -> None:
        self._session = session
        self._familia_id = familia_id
        self._daily_limit = int(os.getenv("LLAMA3_DAILY_QUOTA", str(DEFAULT_DAILY_LIMIT)))
        self._repo = AiUsageRepository(session, familia_id)

    @property
    def daily_limit(self) -> int:
        """Límite diario configurado."""
        return self._daily_limit

    def can_use_llama3(self) -> bool:
        """Retorna True si la familia aún tiene cuota disponible para Llama 3."""
        remaining = self.get_remaining()
        if remaining <= 0:
            logger.info(
                "[QUOTA] Familia %d: cuota Llama 3 agotada (%d/%d)",
                self._familia_id,
                self._daily_limit - remaining,
                self._daily_limit,
            )
            return False
        return True

    def get_remaining(self) -> int:
        """Retorna cuántas consultas Llama 3 quedan hoy."""
        return self._repo.get_remaining_today(self._daily_limit, model="llama3")

    def get_count_today(self) -> int:
        """Retorna cuántas consultas Llama 3 se hicieron hoy."""
        return self._repo.get_count_today(model="llama3")

    def register_llama3_usage(
        self, prompt_tokens: int = 0, completion_tokens: int = 0
    ) -> AiUsage:
        """Registra una consulta a Llama 3."""
        usage = self._repo.register_usage(
            model="llama3",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        logger.info(
            "[QUOTA] Familia %d: Llama 3 usage registrado "
            "(%d/%d, tokens: %d+%d)",
            self._familia_id,
            self.get_count_today(),
            self._daily_limit,
            prompt_tokens,
            completion_tokens,
        )
        return usage

    def register_gemma2_usage(
        self, prompt_tokens: int = 0, completion_tokens: int = 0
    ) -> AiUsage:
        """Registra una consulta a Gemma 2 (sin límite)."""
        return self._repo.register_usage(
            model="gemma2",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    def get_fallback_message(self) -> str:
        """Mensaje para el usuario cuando se agota la cuota."""
        remaining = self.get_remaining()
        if remaining > 0:
            return ""
        return MENSAJE_CUOTA_AGOTADA