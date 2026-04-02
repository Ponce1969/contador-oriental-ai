"""
OCRController: thin controller que orquesta el flujo de procesamiento
de tickets fotográficos. Delega toda la lógica a TicketService.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from result import Result

from controllers.base_controller import BaseController
from models.errors import AppError
from models.ticket_model import PartialExpense
from repositories.expense_repository import ExpenseRepository
from services.ai.ai_advisor_service import AIAdvisorService
from services.ai.embedding_service import EmbeddingService
from services.infrastructure.ocr_service import OCRService
from services.infrastructure.ticket_service import TicketService

logger = logging.getLogger(__name__)


class OCRController(BaseController):
    """
    Controller para procesamiento OCR de tickets de compra.
    Orquesta: OCRService → TicketService → PartialExpense para confirmación.
    El guardado final usa el ExpenseController existente (flujo normal).
    """

    def get_title(self) -> str:
        return "Cargar Ticket"

    async def procesar_ticket(
        self,
        imagen_path: str,
        on_progreso: Callable[[str, str], Awaitable[None]] | None = None,
    ) -> Result[PartialExpense, AppError]:
        """
        Procesa una imagen de ticket y retorna un PartialExpense
        pre-llenado para que el usuario confirme antes de guardar.
        on_progreso(titulo, subtitulo) — callback async para feedback dinámico.
        """
        with self._get_session() as session:
            expense_repo = ExpenseRepository(session, self._familia_id)
            ticket_service = TicketService(
                ocr_service=OCRService(),
                embedding_service=EmbeddingService(),
                expense_repo=expense_repo,
                ai_service=AIAdvisorService(),
            )
            resultado = await ticket_service.procesar_ticket(
                imagen_path,
                on_progreso=on_progreso,
            )

        logger.info(
            "[OCR] Ticket procesado: %s",
            "ok" if hasattr(resultado, "ok") else "err",
        )
        return resultado
