"""
ModelRouter — Decide qué modelo de IA usar basado en la pregunta y contexto.

Lógica de routing:
- Keywords de normativa/fiscal → Llama 3 70B (si hay cuota)
- Rango temporal > 1 mes → Llama 3 70B (si hay cuota)
- Viene del botón "Preguntale al Contador sobre estos 3 meses" → Llama 3 70B
- Simple / clasificación → Gemma 2:2b (local, sin límite)
- Cuota agotada → Gemma 2:2b con aviso
"""
from __future__ import annotations

import logging
import os

from models.ai_model import AIContext

logger = logging.getLogger(__name__)

# Keywords que activan Llama 3 (normativa uruguaya y análisis complejo)
KEYWORDS_LLAMA3: frozenset[str] = frozenset(
    [
        # Normativa uruguaya
        "iva",
        "bps",
        "irpf",
        "dgi",
        "sucive",
        "patente",
        "inclusion financiera",
        "beneficio tarjeta",
        "deduccion",
        "exencion",
        "exención",
        "retencion",
        "retención",
        "tributo",
        "impuesto",
        "afip",
        "monotributo",
        "aportes",
        # Análisis complejo
        "proyeccion",
        "proyección",
        "ahorro",
        "optimizar",
        "planificar",
        "3 meses",
        "tres meses",
        "ultimos meses",
        "últimos meses",
        "historial",
        # Legal
        "ley",
        "decreto",
        "reglamento",
    ]
)


class ModelRouter:
    """
    Decide si usar Gemma 2:2b (local) o Llama 3 70B (cloud).

    Criterios (en orden de prioridad):
    1. Si viene del Historial → Llama 3
    2. Si la pregunta tiene keywords fiscales/normativos → Llama 3
    3. Si el rango temporal abarca > 1 mes → Llama 3
    4. Si el contexto tiene empalme → Llama 3
    5. Si no hay cuota → Gemma 2 con aviso
    6. Default → Gemma 2
    """

    def route(
        self,
        pregunta: str,
        ctx: AIContext | None = None,
        has_quota: bool = True,
        from_history: bool = False,
        range_months: int = 1,
    ) -> str:
        """
        Retorna 'llama3' o 'gemma2' según la pregunta y contexto.

        Args:
            pregunta: La pregunta del usuario en texto libre.
            ctx: Contexto financiero pre-calculado (puede ser None).
            has_quota: Si la familia tiene cuota de Llama 3 disponible.
            from_history: Si la pregunta viene del botón de Historial.
            range_months: Cantidad de meses que abarca la consulta (del QueryAnalyzer).

        Returns:
            'llama3' o 'gemma2'
        """
        pregunta_lower = pregunta.lower()

        # 1. Si viene del Historial → Llama 3 (si hay cuota)
        if from_history:
            if has_quota:
                logger.info("[ROUTER] Historial → Llama 3")
                return "llama3"
            logger.info("[ROUTER] Historial pero sin cuota → Gemma 2 con aviso")
            return "gemma2"

        # 2. Keywords de normativa/fiscal → Llama 3
        for keyword in KEYWORDS_LLAMA3:
            if keyword in pregunta_lower:
                if has_quota:
                    logger.info("[ROUTER] Keyword '%s' → Llama 3", keyword)
                    return "llama3"
                logger.info(
                    "[ROUTER] Keyword '%s' pero sin cuota → Gemma 2", keyword
                )
                return "gemma2"

        # 3. Rango temporal > 1 mes → Llama 3
        if range_months > 1:
            if has_quota:
                logger.info(
                    "[ROUTER] Rango de %d meses → Llama 3", range_months
                )
                return "llama3"
            logger.info(
                "[ROUTER] Rango de %d meses pero sin cuota → Gemma 2", range_months
            )
            return "gemma2"

        # 4. Contexto con empalme (mes anterior) → Llama 3
        if ctx and ctx.empalme_mes_label:
            if has_quota:
                logger.info(
                    "[ROUTER] Contexto con empalme (%s) → Llama 3",
                    ctx.empalme_mes_label,
                )
                return "llama3"
            logger.info("[ROUTER] Contexto con empalme pero sin cuota → Gemma 2")
            return "gemma2"

        # 5. Default → Gemma 2 (local, sin límite)
        logger.info("[ROUTER] Consulta simple → Gemma 2")
        return "gemma2"