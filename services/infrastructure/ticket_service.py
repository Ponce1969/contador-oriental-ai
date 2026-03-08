"""
Orquestador del flujo OCR completo:
  1. OCRService extrae texto crudo con Tesseract
  2. Gemma parsea el texto y extrae monto/fecha/comercio/items
  3. ExpenseRepository busca categoría por similitud cosine
  4. Retorna PartialExpense listo para mostrar al usuario en vista de confirmación
"""
from __future__ import annotations

import json
import logging
import re
from collections import Counter
from collections.abc import Awaitable, Callable
from datetime import date

from result import Err, Ok, Result

from models.errors import AppError
from models.ticket_model import PartialExpense
from services.ai.embedding_service import EmbeddingService
from services.infrastructure.ocr_service import OCRService

logger = logging.getLogger(__name__)

# Prompt estructurado para Gemma — respuesta JSON estricta
# Las llaves dobles {{ }} son escape de str.format()
_PROMPT_PARSEO = (
    "Analizá este texto de un ticket de compra uruguayo y extraé los datos.\n"
    "Respondé ÚNICAMENTE con un JSON válido, sin texto adicional, "
    "en este formato exacto:\n"
    "\n"
    "{{\n"
    '  "monto": 1250.0,\n'
    '  "fecha": "2026-02-28",\n'
    '  "comercio": "Tienda Inglesa",\n'
    '  "items": ["leche", "pan", "aceite"]\n'
    "}}\n"
    "\n"
    "Si no podés determinar un campo, usá null.\n"
    "La fecha debe estar en formato YYYY-MM-DD.\n"
    "El monto debe ser el TOTAL del ticket (número sin símbolos de moneda).\n"
    "\n"
    "Texto del ticket:\n"
    "{texto}"
)


class TicketService:
    """Orquesta OCR + parseo Gemma + sugerencia de categoría."""

    def __init__(
        self,
        ocr_service: OCRService,
        embedding_service: EmbeddingService,
        expense_repo,       # ExpenseRepository — inyectado
        ai_service,         # AIAdvisorService — inyectado para llamada_directa()
    ):
        self.ocr = ocr_service
        self.embedding = embedding_service
        self.expense_repo = expense_repo
        self.ai_service = ai_service

    async def procesar_ticket(
        self,
        imagen_path: str,
        on_progreso: Callable[[str, str], Awaitable[None]] | None = None,
    ) -> Result[PartialExpense, AppError]:
        """Flujo completo: imagen → PartialExpense con categoría sugerida."""

        async def progreso(titulo: str, sub: str = ""):
            if on_progreso:
                await on_progreso(titulo, sub)

        # 1. Extraer texto con Tesseract
        await progreso("Extrayendo texto...", "Tesseract OCR con preprocesado PIL")
        ocr_result = await self.ocr.extraer_texto(imagen_path)
        if isinstance(ocr_result, Err):
            return ocr_result

        partial = ocr_result.ok()

        if partial.confianza_ocr < 0.3:
            logger.warning(
                "[TICKET] Confianza OCR baja (%.2f) — imagen de mala calidad",
                partial.confianza_ocr,
            )

        # 2. Parsear con Gemma
        await progreso(
            "Gemma está analizando los datos...",
            f"{len(partial.texto_crudo)} caracteres detectados",
        )
        parsed = await self._parsear_con_gemma(partial.texto_crudo)
        if parsed:
            partial.monto = parsed.get("monto")
            partial.comercio = parsed.get("comercio")
            partial.items = parsed.get("items") or []

            # Convertir fecha string a date si viene de Gemma
            fecha_str = parsed.get("fecha")
            if fecha_str:
                try:
                    partial.fecha = date.fromisoformat(fecha_str)
                except (ValueError, TypeError):
                    partial.fecha = None

        # 3. Sugerir categoría via cosine search
        await progreso(
            "Buscando categoría...",
            "Similitud cosine sobre gastos históricos",
        )
        termino = partial.comercio or " ".join(partial.items[:3])
        if termino:
            partial.categoria_sugerida = await self._sugerir_categoria(termino)

        logger.info(
            "[TICKET] Procesado: comercio=%s monto=%s categoria=%s confianza=%.2f",
            partial.comercio,
            partial.monto,
            partial.categoria_sugerida,
            partial.confianza_ocr,
        )
        return Ok(partial)

    async def _parsear_con_gemma(self, texto: str) -> dict | None:
        """
        Pide a Gemma que extraiga monto/fecha/comercio/items del texto crudo.
        Parser defensivo: si Gemma devuelve basura, retorna None
        y el usuario completa manualmente en la vista de confirmación.
        """
        if not texto.strip():
            return None
        try:
            prompt = _PROMPT_PARSEO.format(texto=texto[:1500])
            respuesta = await self.ai_service.llamada_directa(prompt)

            if not respuesta:
                logger.warning("[TICKET] Gemma devolvió respuesta vacía")
                return None

            # Buscar JSON — Gemma a veces agrega texto antes/después
            match = re.search(r'\{.*?\}', respuesta, re.DOTALL)
            if not match:
                logger.warning("[TICKET] Gemma no devolvió JSON válido")
                return None

            datos = json.loads(match.group())
            logger.info(
                "[TICKET] Gemma parseó: comercio=%s monto=%s",
                datos.get("comercio"),
                datos.get("monto"),
            )
            return datos

        except (json.JSONDecodeError, Exception) as e:
            logger.warning("[TICKET] Error parseando respuesta de Gemma: %s", e)
            return None

    async def _sugerir_categoria(self, termino: str) -> str | None:
        """Busca la categoría más probable via cosine search en expenses.embedding."""
        try:
            emb_result = await self.embedding.generar_embedding(termino)
            if isinstance(emb_result, Err):
                return None
            resultados = self.expense_repo.buscar_por_similitud(
                emb_result.ok(), umbral_cosine=0.25
            )
            if resultados:
                cats = Counter(g.categoria.value for g, _ in resultados)
                return cats.most_common(1)[0][0]
        except Exception as e:
            logger.warning("[TICKET] Error sugiriendo categoría: %s", e)
        return None
