"""
MemoryEventHandler — Observer que escucha eventos contables y los vectoriza.
Se suscribe al EventSystem y llama a IAMemoryService en background.
"""
from __future__ import annotations

import logging
from typing import Any

from core.events import Event, EventType
from services.ia_memory_service import IAMemoryService

logger = logging.getLogger(__name__)


class MemoryEventHandler:
    """
    Handler Observer para registrar eventos contables en la memoria vectorial.
    Se ejecuta en background: no bloquea la UI de Flet.
    """

    def __init__(self, memory_service: IAMemoryService) -> None:
        self.memory_service = memory_service

    async def handle(self, event: Event) -> None:
        """Despachar evento al formateador correcto y memorizar."""
        try:
            if event.type == EventType.GASTO_CREADO:
                texto = self._formatear_gasto(event.data)
                await self.memory_service.registrar_evento_contable(
                    texto_plano=texto,
                    source_type=event.type.value,
                    source_id=event.source_id,
                )
                await self._guardar_embedding_en_gasto(
                    texto=texto,
                    expense_id=event.source_id,
                    familia_id=event.familia_id,
                )
                return
            elif event.type == EventType.INGRESO_CREADO:
                texto = self._formatear_ingreso(event.data)
            elif event.type == EventType.SNAPSHOT_CREADO:
                texto = self._formatear_snapshot(event.data)
            elif event.type == EventType.OCR_PROCESADO:
                texto = self._formatear_ocr(event.data)
            else:
                return

            await self.memory_service.registrar_evento_contable(
                texto_plano=texto,
                source_type=event.type.value,
                source_id=event.source_id,
            )

        except Exception as e:
            logger.error(
                "[MEMORY_HANDLER] familia_id=%s event_type=%s error=%s",
                event.familia_id,
                event.type.value,
                str(e),
            )

    async def _guardar_embedding_en_gasto(
        self,
        texto: str,
        expense_id: int | None,
        familia_id: int,
    ) -> None:
        """Genera el embedding y lo guarda en expenses.embedding (fire-and-forget)."""
        if expense_id is None:
            return
        from result import Err
        from database.engine import get_session
        from repositories.expense_repository import ExpenseRepository

        embedding_result = await self.memory_service.embedding_service.generar_embedding(texto)
        if isinstance(embedding_result, Err):
            logger.warning(
                "[MEMORY_HANDLER] No se pudo generar embedding para gasto id=%s", expense_id
            )
            return

        session = get_session()
        try:
            repo = ExpenseRepository(session, familia_id)
            repo.guardar_embedding(expense_id, embedding_result.ok())
            logger.info("[MEMORY_HANDLER] Embedding guardado en expenses id=%s", expense_id)
        except Exception as e:
            session.rollback()
            logger.error("[MEMORY_HANDLER] Error guardando embedding gasto id=%s: %s", expense_id, e)
        finally:
            session.close()

    def _formatear_gasto(self, data: dict[str, Any]) -> str:
        return (
            f"Gasto registrado: {data.get('descripcion', '')} "
            f"por ${data.get('monto', 0):,.0f} "
            f"en categoría {data.get('categoria', '')}. "
            f"Método: {data.get('metodo_pago', '')}. "
            f"Fecha: {data.get('fecha', '')}."
        )

    def _formatear_ingreso(self, data: dict[str, Any]) -> str:
        return (
            f"Ingreso registrado: {data.get('descripcion', '')} "
            f"por ${data.get('monto', 0):,.0f} "
            f"en categoría {data.get('categoria', '')}. "
            f"Miembro: {data.get('miembro', '')}. "
            f"Fecha: {data.get('fecha', '')}."
        )

    def _formatear_snapshot(self, data: dict[str, Any]) -> str:
        return (
            f"Snapshot mensual: {data.get('categoria', '')} "
            f"total ${data.get('total_dinero', 0):,.0f} "
            f"en {data.get('cantidad_compras', 0)} compras. "
            f"Ticket promedio: ${data.get('ticket_promedio', 0):,.0f}. "
            f"Período: {data.get('mes', '')}/{data.get('anio', '')}."
        )

    def _formatear_ocr(self, data: dict[str, Any]) -> str:
        return (
            f"Ticket procesado por OCR: {data.get('texto_extraido', '')}. "
            f"Total estimado: ${data.get('total_estimado', 0):,.0f}. "
            f"Comercio: {data.get('comercio', '')}. "
            f"Fecha: {data.get('fecha', '')}."
        )
