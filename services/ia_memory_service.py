"""
IAMemoryService — Orquestador de memoria vectorial para el Contador Oriental.
Coordina EmbeddingService + MemoriaRepository para guardar y recuperar recuerdos.
"""
from __future__ import annotations

import logging

from result import Err, Ok, Result

from models.errors import AppError
from repositories.memoria_repository import MemoriaRepository
from services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 15000


class IAMemoryService:
    """
    Servicio de memoria vectorial para el Contador Oriental.

    Flujo de guardado:
        texto → EmbeddingService → vector 768d → MemoriaRepository → PostgreSQL

    Flujo de consulta:
        pregunta → embedding → HNSW cosine search → contexto relevante
    """

    def __init__(
        self,
        memoria_repo: MemoriaRepository,
        embedding_service: EmbeddingService,
    ) -> None:
        self.repo = memoria_repo
        self.embedding_service = embedding_service

    async def registrar_evento_contable(
        self,
        texto_plano: str,
        source_type: str | None = None,
        source_id: int | None = None,
    ) -> Result[int, AppError]:
        """
        Vectorizar y guardar un evento contable en la memoria permanente.

        Args:
            texto_plano: Narrativa del evento (ej: "Gasto $3500 UTE hogar").
            source_type: Tipo de origen ('expense', 'income', 'snapshot').
            source_id: ID del registro original en su tabla.

        Returns:
            Ok(id) del registro creado, o Err si falla.
        """
        if not texto_plano or not texto_plano.strip():
            return Err(AppError(message="Texto vacío: no se puede memorizar."))

        embedding_result = await self.embedding_service.generar_embedding(texto_plano)

        if isinstance(embedding_result, Err):
            logger.warning(
                "[MEMORY] Embedding fallido para source_type=%s source_id=%s: %s",
                source_type,
                source_id,
                embedding_result.err(),
            )
            return Err(embedding_result.err())

        record_id = self.repo.guardar(
            content=texto_plano,
            embedding=embedding_result.ok(),
            source_type=source_type,
            source_id=source_id,
        )

        if record_id is None:
            return Err(AppError(message="No se pudo guardar en memoria vectorial."))

        logger.info(
            "[MEMORY] Recuerdo guardado id=%s source_type=%s source_id=%s",
            record_id,
            source_type,
            source_id,
        )
        return Ok(record_id)

    async def buscar_contexto_para_pregunta(
        self,
        pregunta: str,
        limit: int = 5,
        source_type: str | None = None,
    ) -> Result[list[str], AppError]:
        """
        Buscar recuerdos semánticamente similares para enriquecer el prompt RAG.

        Args:
            pregunta: Pregunta del usuario en texto libre.
            limit: Número máximo de recuerdos a recuperar.
            source_type: Filtrar por tipo de fuente.

        Returns:
            Ok([texto, ...]) con los contextos más relevantes, respetando
            el límite de tokens de Gemma 2:2b (~3750 tokens = 15000 chars).
        """
        embedding_result = await self.embedding_service.generar_embedding(pregunta)

        if isinstance(embedding_result, Err):
            logger.warning(
                "[MEMORY] No se pudo generar embedding de consulta: %s",
                embedding_result.err(),
            )
            return Err(embedding_result.err())

        recuerdos = self.repo.buscar_similares(
            embedding=embedding_result.ok(),
            limit=limit,
            source_type=source_type,
        )

        if not recuerdos:
            return Ok([])

        contextos = [r["content"] for r in recuerdos]

        contextos_validos: list[str] = []
        longitud_acumulada = 0
        for ctx in contextos:
            if longitud_acumulada + len(ctx) > MAX_CONTEXT_CHARS:
                break
            contextos_validos.append(ctx)
            longitud_acumulada += len(ctx)

        logger.info(
            "[MEMORY] Contexto recuperado: %d recuerdos (%d chars) para '%s...'",
            len(contextos_validos),
            longitud_acumulada,
            pregunta[:50],
        )
        return Ok(contextos_validos)

    def tiene_memoria(self) -> bool:
        """Verificar si hay registros en memoria para esta familia."""
        return self.repo.count() > 0
