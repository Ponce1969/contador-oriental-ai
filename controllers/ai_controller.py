"""Controlador para el Contador Oriental"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal

from result import Result

from controllers.base_controller import BaseController
from controllers.exchange_rate_controller import ExchangeRateController
from core.state import AppState
from models.ai_model import AIContext, AIRequest, AIResponse
from models.errors import AppError
from models.expense_model import Expense
from controllers.installment_controller import InstallmentController
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

_MESES_NUM: dict[int, str] = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


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
    ) -> tuple[Decimal, str]:
        """
        Busca gastos semánticamente similares a la pregunta usando
        pgvector cosine distance sobre expenses.embedding.
        Retorna (subtotal, label) — (Decimal('0'), '') si no hay resultados.
        """
        from result import Err

        embedding_result = await self.embedding_service.generar_embedding(pregunta)
        if isinstance(embedding_result, Err):
            logger.warning(
                "[SUBTOTAL] No se pudo generar embedding: %s", embedding_result.err()
            )
            return Decimal("0"), ""

        emb = embedding_result.ok()
        repo = ExpenseRepository(session, self._familia_id)
        resultados = repo.buscar_por_similitud(emb, umbral_cosine=umbral_cosine)

        if not resultados:
            logger.info("[SUBTOTAL] Sin resultados cosine para: %s", pregunta)
            return Decimal("0"), ""

        subtotal = sum((g.monto for g, _ in resultados), Decimal("0"))
        label = pregunta.strip()[:40]
        logger.info(
            "[SUBTOTAL] %d gastos cosine (umbral=%.2f) -> %s",
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
        Si el QueryAnalyzer detecta un rango (ej: "abril"), sincroniza gastos,
        ingresos y comparativa a ese rango.
        Si el mes actual tiene pocos movimientos (< 5 gastos), inyecta el cierre
        del mes anterior como contexto de empalme.
        """
        with self._get_session() as session:
            ahora = datetime.now()
            mes_actual = ahora.month
            anio_actual = ahora.year

            expense_repo = ExpenseRepository(session, self._familia_id)
            expense_service = ExpenseService(expense_repo)
            income_repo = IncomeRepository(session, self._familia_id)
            income_service = IncomeService(income_repo)

            intencion = QueryAnalyzer.detectar_intenciones(pregunta)

            # ── Gastos: rango detectado o mes actual ──────────────────────
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

            # ── Ingresos: mismo rango que gastos ──────────────────────────
            if intencion.rango:
                mes_ini, anio_ini, mes_fin, anio_fin = intencion.rango
                ingresos: list = []
                m, a = mes_ini, anio_ini
                while (a, m) <= (anio_fin, mes_fin):
                    ingresos += list(income_repo.get_by_month(a, m))
                    m += 1
                    if m > 12:
                        m = 1
                        a += 1
                logger.info(
                    "[RANGO] %d ingresos históricos cargados (%d/%d→%d/%d)",
                    len(ingresos),
                    mes_ini,
                    anio_ini,
                    mes_fin,
                    anio_fin,
                )
            else:
                ingresos = [
                    i
                    for i in income_service.list_incomes()
                    if i.fecha.month == mes_actual and i.fecha.year == anio_actual
                ]
            ingresos_total = sum((i.monto for i in ingresos), Decimal("0"))

            # ── Filtrado por categorías ───────────────────────────────────
            gastos_filtrados = filtrar_por_categorias(gastos_mes, intencion.categorias)

            total_gastos_mes = sum(
                (g.monto for g in gastos_mes), Decimal("0")
            )
            resumen_gastos: dict[str, dict[str, dict]] = {}
            total_gastos_count = 0
            if gastos_filtrados:
                resumen_gastos = agrupar_gastos(gastos_filtrados)
                total_gastos_count = len(gastos_filtrados)

            subtotal_desc, label_desc = await self._calcular_subtotal_semantico(
                pregunta, session
            )

            # ── Miembros ──────────────────────────────────────────────────
            member_repo = FamilyMemberRepository(session, self._familia_id)
            member_service = FamilyMemberService(member_repo)
            miembros = member_service.list_members()

            # ── Comparativa: relativa al rango o mes actual ──────────────
            if intencion.rango:
                _, _, mes_target, anio_target = intencion.rango
            else:
                mes_target = mes_actual
                anio_target = anio_actual

            mes_prev = mes_target - 1 if mes_target > 1 else 12
            anio_prev = anio_target if mes_target > 1 else anio_target - 1

            snapshot_repo = MonthlySnapshotRepository(session, self._familia_id)
            comparativa: list = []
            try:
                snapshot_repo.upsert_mes_actual(anio_target, mes_target)
                snapshot_repo.upsert_mes_actual(anio_prev, mes_prev)
                comparativa = snapshot_repo.obtener_comparativa_mensual(
                    anio_target, mes_target
                )
            except Exception as snap_err:
                logger.warning("Comparativa no disponible: %s", snap_err)

            # ── Empalme: cierre del mes anterior si mes actual tiene pocos
            #    movimientos y no hay rango explícito ─────────────────────
            empalme_gastos: dict = {}
            empalme_ingresos_total = Decimal("0")
            empalme_mes_label = ""
            empalme_total_gastos = Decimal("0")

            if not intencion.rango and len(gastos_mes) < 5:
                mes_emp = mes_prev  # = mes_actual - 1 ya calculado
                anio_emp = anio_prev
                gastos_emp = list(expense_repo.get_by_month(anio_emp, mes_emp))
                if gastos_emp:
                    gastos_emp_filtrados = filtrar_por_categorias(
                        gastos_emp, intencion.categorias
                    )
                    empalme_gastos = (
                        agrupar_gastos(gastos_emp_filtrados)
                        if gastos_emp_filtrados
                        else {}
                    )
                    empalme_total_gastos = sum(
                        (g.monto for g in gastos_emp), Decimal("0")
                    )
                    ingresos_emp = list(income_repo.get_by_month(anio_emp, mes_emp))
                    empalme_ingresos_total = sum(
                        (i.monto for i in ingresos_emp), Decimal("0")
                    )
                    empalme_mes_label = f"{_MESES_NUM[mes_emp]} {anio_emp}"
                    logger.info(
                        "[EMPALME] Cierre de %s: %d gastos ($%s), ingresos $%s",
                        empalme_mes_label,
                        len(gastos_emp),
                        empalme_total_gastos,
                        empalme_ingresos_total,
                    )

            # ── Proyección de cuotas futuras ───────────────────────────────
            proyeccion = {}
            try:
                inst_ctrl = InstallmentController(familia_id=self._familia_id)
                proyeccion = inst_ctrl.proyectar_meses(6)
            except Exception as proy_err:
                logger.warning("Proyeccion no disponible: %s", proy_err)

            # ── Cotización del dólar ──────────────────────────────────────
            exchange_ctrl = ExchangeRateController()
            cotizacion, _ = exchange_ctrl.get_display_rate()

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
                proyeccion_cuotas=proyeccion,
                cotizacion_dolar=cotizacion if cotizacion > 0 else None,
                empalme_gastos=empalme_gastos,
                empalme_ingresos_total=empalme_ingresos_total,
                empalme_mes_label=empalme_mes_label,
                empalme_total_gastos=empalme_total_gastos,
            )

    async def _buscar_memoria_vectorial(self, pregunta: str, ctx: AIContext) -> str:
        """Recupera contexto de memoria vectorial RAG para enriquecer la respuesta.

        Siempre consulta la memoria vectorial: incluso con gastos del mes,
        el contexto histórico de meses anteriores es valioso para la IA.
        """
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
        self, pregunta: str, incluir_gastos: bool = True, from_history: bool = False
    ) -> Result[AIResponse, AppError]:
        """
        Consulta al Contador Oriental con detección inteligente de contexto.
        La parte de IA es asíncrona; la BD permanece síncrona.

        Args:
            pregunta: Pregunta del usuario
            incluir_gastos: Si incluir gastos recientes en el contexto
            from_history: Si la pregunta viene del botón de Historial

        Returns:
            Result con la respuesta del contador o error
        """
        logger.info(f"Consulta recibida: '{pregunta}' (from_history={from_history})")

        # Detectar rango temporal para routing
        intencion = QueryAnalyzer.detectar_intenciones(pregunta)
        range_months = 1
        if intencion.rango:
            mes_ini, anio_ini, mes_fin, anio_fin = intencion.rango
            range_months = (anio_fin - anio_ini) * 12 + (mes_fin - mes_ini) + 1
            logger.info("[RANGO] Consulta abarca %d meses", range_months)

        # Verificar cuota de Llama 3
        has_quota = True
        with self._get_session() as session:
            from services.infrastructure.quota_manager import QuotaManager

            quota = QuotaManager(session, self._familia_id)
            has_quota = quota.can_use_llama3()

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

        result = await self.ai_service.consultar(
            request,
            ctx=ctx,
            memoria_vectorial=memoria_str,
            has_quota=has_quota,
            from_history=from_history,
            range_months=range_months,
        )

        # Registrar uso de modelo en cuota
        if result.is_ok():
            modelo_usado = "llama3" if (has_quota and from_history) else "gemma2"
            # El router decide internamente, pero registramos lo que se usó
            # Esto se podría mejorar extrayendo el modelo del resultado
            with self._get_session() as session:
                from services.infrastructure.quota_manager import QuotaManager

                quota = QuotaManager(session, self._familia_id)
                if modelo_usado == "llama3":
                    quota.register_llama3_usage()
                else:
                    quota.register_gemma2_usage()

        return result

    async def consultar_contador_stream(
        self,
        pregunta: str,
        incluir_gastos: bool = True,
        from_history: bool = False,
    ):
        """
        Versión streaming de consultar_contador().
        Prepara el mismo AIContext y yield tokens a medida que el modelo responde.
        Soporta routing híbrido: Llama 3 (cloud) o Gemma 2 (local).

        Args:
            pregunta: Pregunta del usuario
            incluir_gastos: Si incluir gastos recientes en el contexto
            from_history: Si la pregunta viene del botón de Historial

        Yields:
            str — fragmento de texto del modelo.
        """
        logger.info("Stream consulta: '%s' (from_history=%s)", pregunta, from_history)

        # Detectar rango temporal para routing
        intencion = QueryAnalyzer.detectar_intenciones(pregunta)
        range_months = 1
        if intencion.rango:
            mes_ini, anio_ini, mes_fin, anio_fin = intencion.rango
            range_months = (anio_fin - anio_ini) * 12 + (mes_fin - mes_ini) + 1
            logger.info("[RANGO] Consulta abarca %d meses", range_months)

        # Verificar cuota de Llama 3
        has_quota = True
        with self._get_session() as session:
            from services.infrastructure.quota_manager import QuotaManager

            quota = QuotaManager(session, self._familia_id)
            has_quota = quota.can_use_llama3()

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

        # Determinar modelo para registro de cuota
        from services.ai.model_router import ModelRouter

        router = ModelRouter()
        modelo = router.route(
            pregunta=pregunta,
            ctx=ctx,
            has_quota=has_quota,
            from_history=from_history,
            range_months=range_months,
        )

        async for token in self.ai_service.consultar_stream(
            request,
            ctx=ctx,
            memoria_vectorial=memoria_str,
            has_quota=has_quota,
            from_history=from_history,
            range_months=range_months,
        ):
            yield token

        # Registrar uso después del stream
        with self._get_session() as session:
            from services.infrastructure.quota_manager import QuotaManager

            quota = QuotaManager(session, self._familia_id)
            if modelo == "llama3":
                quota.register_llama3_usage()
            else:
                quota.register_gemma2_usage()

    def get_title(self) -> str:
        """Título de la vista"""
        return "🧮 Contador Oriental"

    def get_description(self) -> str:
        """Descripción del servicio"""
        return "Asistente contable con IA para familias uruguayas"
