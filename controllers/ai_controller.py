"""Controlador para el Contador Oriental"""

from __future__ import annotations

import logging
from datetime import datetime

from result import Result

from controllers.base_controller import BaseController
from models.ai_model import AIContext, AIRequest, AIResponse
from models.errors import AppError
from models.expense_model import Expense
from repositories.expense_repository import ExpenseRepository
from repositories.family_member_repository import FamilyMemberRepository
from repositories.income_repository import IncomeRepository
from repositories.memoria_repository import MemoriaRepository
from repositories.monthly_snapshot_repository import MonthlySnapshotRepository
from services.ai.ai_advisor_service import AIAdvisorService
from services.ai.embedding_service import EmbeddingService
from services.ai.expense_formatters import (
    agrupar_gastos,
    filtrar_por_categorias,
    resumir_metodos_pago,
)
from services.ai.ia_memory_service import IAMemoryService
from services.ai.query_analyzer import QueryAnalyzer
from services.domain.expense_service import ExpenseService
from services.domain.family_member_service import FamilyMemberService
from services.domain.income_service import IncomeService

logger = logging.getLogger(__name__)


class AIController(BaseController):
    """Controlador para interactuar con el Contador Oriental"""

    def __init__(self, familia_id: int):
        super().__init__(familia_id=familia_id)
        self.ai_service = AIAdvisorService()
        self.embedding_service = EmbeddingService()
        self.last_context: AIContext = AIContext()
        self.last_pregunta: str = ""

    def _get_memory_service(self, session) -> IAMemoryService:
        """Crear IAMemoryService con sesión activa."""
        repo = MemoriaRepository(session, self._familia_id or 0)
        return IAMemoryService(repo, self.embedding_service)

    async def _calcular_subtotal_semantico(
        self,
        pregunta: str,
        session,
        umbral_cosine: float = 0.30,
    ) -> tuple[float, str]:
        """
        Busca gastos semánticamente similares a la pregunta usando
        pgvector cosine distance sobre expenses.embedding.
        Retorna (subtotal, label) — (0.0, '') si no hay resultados.
        """
        from result import Err

        embedding_result = await self.embedding_service.generar_embedding(pregunta)
        if isinstance(embedding_result, Err):
            logger.warning(
                "[SUBTOTAL] No se pudo generar embedding: %s", embedding_result.err()
            )
            return 0.0, ""

        emb = embedding_result.ok()
        repo = ExpenseRepository(session, self._familia_id)
        resultados = repo.buscar_por_similitud(emb, umbral_cosine=umbral_cosine)

        if not resultados:
            logger.info("[SUBTOTAL] Sin resultados cosine para: %s", pregunta)
            return 0.0, ""

        subtotal = sum(g.monto for g, _ in resultados)
        label = pregunta.strip()[:40]
        logger.info(
            "[SUBTOTAL] %d gastos cosine (umbral=%.2f) → $%.0f",
            len(resultados),
            umbral_cosine,
            subtotal,
        )
        return subtotal, label

    async def _construir_contexto(
        self,
        pregunta: str,
    ) -> AIContext:
        """Construye el AIContext con datos financieros del mes para una pregunta.
        Extrae gastos, ingresos, miembros, snapshot comparativo y subtotal semántico.
        Usado tanto por consultar_contador como por consultar_contador_stream.
        """
        with self._get_session() as session:
            ahora = datetime.now()
            mes_actual = ahora.month
            anio_actual = ahora.year

            expense_repo = ExpenseRepository(session, self._familia_id)
            expense_service = ExpenseService(expense_repo)

            intencion = QueryAnalyzer.detectar_intenciones(pregunta)
            if intencion.rango:
                mes_ini, anio_ini, mes_fin, anio_fin = intencion.rango
                gastos_mes: list[Expense] = []
                m, a = mes_ini, anio_ini
                while (a, m) <= (anio_fin, mes_fin):
                    gastos_mes += list(expense_repo.get_by_month(a, m))
                    m += 1
                    if m > 12:
                        m = 1
                        a += 1
                logger.info(
                    "[RANGO] %d gastos históricos cargados (%d/%d→%d/%d)",
                    len(gastos_mes),
                    mes_ini,
                    anio_ini,
                    mes_fin,
                    anio_fin,
                )
            else:
                gastos_mes = [
                    g
                    for g in expense_service.list_expenses()
                    if g.fecha.month == mes_actual and g.fecha.year == anio_actual
                ]

            gastos_filtrados = filtrar_por_categorias(gastos_mes, intencion.categorias)

            total_gastos_mes = sum(g.monto for g in gastos_mes)
            resumen_gastos: dict[str, dict[str, dict]] = {}
            total_gastos_count = 0
            if gastos_filtrados:
                resumen_gastos = agrupar_gastos(gastos_filtrados)
                total_gastos_count = len(gastos_filtrados)

            subtotal_desc, label_desc = await self._calcular_subtotal_semantico(
                pregunta, session
            )

            income_repo = IncomeRepository(session, self._familia_id)
            income_service = IncomeService(income_repo)
            ingresos = [
                i
                for i in income_service.list_incomes()
                if i.fecha.month == mes_actual and i.fecha.year == anio_actual
            ]
            ingresos_total = sum(i.monto for i in ingresos)

            member_repo = FamilyMemberRepository(session, self._familia_id)
            member_service = FamilyMemberService(member_repo)
            miembros = member_service.list_members()

            snapshot_repo = MonthlySnapshotRepository(session, self._familia_id)
            comparativa: list = []
            try:
                snapshot_repo.upsert_mes_actual(anio_actual, mes_actual)
                comparativa = snapshot_repo.obtener_comparativa_mensual(
                    anio_actual, mes_actual
                )
            except Exception as snap_err:
                logger.warning("Comparativa no disponible: %s", snap_err)

            return AIContext(
                resumen_gastos=resumen_gastos,
                total_gastos_count=total_gastos_count,
                total_gastos_mes=total_gastos_mes,
                ingresos_total=ingresos_total,
                miembros_count=len(miembros),
                resumen_metodos_pago=resumir_metodos_pago(gastos_mes),
                comparativa_meses=comparativa,
                subtotal_descripcion=subtotal_desc if subtotal_desc else None,
                terminos_buscados=label_desc,
            )

    async def _buscar_memoria_vectorial(self, pregunta: str, ctx: AIContext) -> str:
        """Recupera contexto de memoria vectorial RAG solo si no hay datos reales del mes."""
        if bool(ctx.resumen_gastos):
            logger.info(
                "[MEMORY] Omitiendo memoria vectorial: hay %d gastos reales del mes.",
                ctx.total_gastos_count,
            )
            return ""
        try:
            with self._get_session() as session:
                memory_service = self._get_memory_service(session)
                if not memory_service.tiene_memoria():
                    return ""
                from result import Ok as MemOk

                mem_result = await memory_service.buscar_contexto_para_pregunta(
                    pregunta=pregunta, limit=5
                )
                if isinstance(mem_result, MemOk) and mem_result.ok():
                    logger.info(
                        "Memoria vectorial: %d recuerdos recuperados",
                        len(mem_result.ok()),
                    )
                    return "\n".join(f"- {c}" for c in mem_result.ok())
        except Exception as mem_err:
            logger.warning("[MEMORY] No se pudo recuperar contexto: %s", mem_err)
        return ""

    async def consultar_contador(
        self, pregunta: str, incluir_gastos: bool = True
    ) -> Result[AIResponse, AppError]:
        """
        Consulta al Contador Oriental con detección inteligente de contexto.
        La parte de IA es asíncrona; la BD permanece síncrona.

        Args:
            pregunta: Pregunta del usuario
            incluir_gastos: Si incluir gastos recientes en el contexto

        Returns:
            Result con la respuesta del contador o error
        """
        logger.info(f"Consulta recibida: '{pregunta}'")

        # Crear request
        request = AIRequest(
            pregunta=pregunta,
            familia_id=self._familia_id,
            incluir_gastos_recientes=incluir_gastos,
        )

        ctx = AIContext()
        if incluir_gastos:
            ctx = await self._construir_contexto(pregunta)

        self.last_context = ctx
        self.last_pregunta = pregunta

        memoria_str = await self._buscar_memoria_vectorial(pregunta, ctx)

        return await self.ai_service.consultar(
            request, ctx=ctx, memoria_vectorial=memoria_str
        )

    async def consultar_contador_stream(
        self,
        pregunta: str,
        incluir_gastos: bool = True,
    ):
        """
        Versión streaming de consultar_contador().
        Prepara el mismo AIContext y yield tokens a medida que Gemma responde.
        La vista actualiza la burbuja token a token.

        Yields:
            str — fragmento de texto del modelo.
        """
        logger.info("Stream consulta: '%s'", pregunta)

        request = AIRequest(
            pregunta=pregunta,
            familia_id=self._familia_id,
            incluir_gastos_recientes=incluir_gastos,
        )

        ctx = AIContext()
        if incluir_gastos:
            ctx = await self._construir_contexto(pregunta)

        self.last_context = ctx
        self.last_pregunta = pregunta

        memoria_str = await self._buscar_memoria_vectorial(pregunta, ctx)

        async for token in self.ai_service.consultar_stream(
            request, ctx=ctx, memoria_vectorial=memoria_str
        ):
            yield token

    def get_title(self) -> str:
        """Título de la vista"""
        return "🧮 Contador Oriental"

    def get_description(self) -> str:
        """Descripción del servicio"""
        return "Asistente contable con IA para familias uruguayas"
