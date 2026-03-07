"""Controlador para el Contador Oriental"""

from __future__ import annotations

import difflib
import logging
import re
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
from services.domain.expense_service import ExpenseService
from services.domain.family_member_service import FamilyMemberService
from services.ai.ia_memory_service import IAMemoryService
from services.domain.income_service import IncomeService

logger = logging.getLogger(__name__)


class AIController(BaseController):
    """Controlador para interactuar con el Contador Oriental"""

    # Palabras temporales/comunes que NO deben hacer fuzzy match con keywords de categorías
    _PALABRAS_TEMPORALES = frozenset([
        "pasado", "pasada", "anterior", "anteriores", "previo", "previa",
        "ultimo", "última", "ultimos", "últimas", "actual", "reciente",
        "meses", "semana", "semanas", "dias", "años", "año",
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
        "cuanto", "cuánto", "cual", "cuál", "como", "cómo", "cuando", "cuándo",
        "gaste", "gasté", "total", "resumen", "gasto", "gastos",
    ])

    # Meses en español → número
    _MESES_ES = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
        "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
        "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    }

    # Diccionario de palabras clave mapeadas a valores reales de ExpenseCategory
    # Las keys son los valores EXACTOS de la BD (con emojis)
    CATEGORY_KEYWORDS: dict[str, list[str]] = {
        "🛒 Almacén": [
            "super", "supermercado", "comida", "almacen", "almacén",
            "compras", "comestibles", "mercado", "verduleria", "verdulería",
            "carniceria", "carnicería", "panaderia", "panadería", "delivery"
        ],
        "🚗 Vehículos": [
            "nafta", "combustible", "gasolina", "auto", "coche", "vehiculo",
            "vehículo", "transporte", "peaje", "estacionamiento", "patente",
            "seguro auto", "mantenimiento auto"
        ],
        "🏠 Hogar": [
            "luz", "agua", "gas", "internet", "telefono", "teléfono",
            "cable", "alquiler", "casa", "hogar", "expensas", "servicio"
        ],
        "👨‍⚕️ Salud": [
            "farmacia", "medico", "médico", "doctor", "hospital",
            "clinica", "clínica", "medicamento", "salud", "consulta",
            "obra social", "odontologo", "odontólogo"
        ],
        "🎉 Ocio": [
            "cine", "teatro", "salida", "restaurante", "cena",
            "asado", "bar", "cerveza", "entretenimiento", "ocio",
            "vacaciones", "paseo", "streaming", "netflix", "spotify"
        ],
        "📚 Educación": [
            "escuela", "colegio", "universidad", "curso", "libro",
            "material", "educacion", "educación", "estudio", "utiles", "útiles"
        ],
        "👕 Ropa": [
            "ropa", "vestimenta", "calzado", "zapato", "remera",
            "pantalon", "pantalón", "campera", "abrigo", "zapatilla"
        ],
        "💳 Otros": [
            "impuesto", "seguro", "prestamo", "préstamo", "varios"
        ]
    }
    
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
    
    def _detectar_categorias_relevantes(self, pregunta: str) -> list[str]:
        """
        Detecta categorías relevantes en la pregunta del usuario.
        Mejorado con fuzzy matching para typos (ej: 'alamcen' -> 'almacén')
        y tokenización para evitar falsos positivos (ej: 'gastos' != 'gas').
        
        Args:
            pregunta: Pregunta del usuario en texto libre
            
        Returns:
            Lista de categorías detectadas (vacía si es consulta general)
        """
        query_lower = pregunta.lower()
        palabras_pregunta = re.findall(r'\w+', query_lower)
        categorias_detectadas: list[str] = []
        
        for categoria, keywords in self.CATEGORY_KEYWORDS.items():
            match_encontrado = False
            
            for keyword in keywords:
                # Caso 1: Keyword compuesta (ej: "seguro auto") -> Búsqueda exacta de frase
                if " " in keyword:
                    if keyword in query_lower:
                        match_encontrado = True
                        break
                
                # Caso 2: Keyword simple -> Búsqueda exacta o fuzzy en palabras
                else:
                    # Coincidencia exacta
                    if keyword in palabras_pregunta:
                        match_encontrado = True
                        break
                    
                    # Fuzzy matching (typos) — excluye palabras temporales/comunes
                    candidatos = [
                        p for p in palabras_pregunta
                        if p not in self._PALABRAS_TEMPORALES
                    ]
                    matches = difflib.get_close_matches(
                        keyword, candidatos, n=1, cutoff=0.88
                    )
                    if matches:
                        logger.info(
                            f"Fuzzy match: '{matches[0]}' -> '{keyword}' ({categoria})"
                        )
                        match_encontrado = True
                        break
            
            if match_encontrado:
                categorias_detectadas.append(categoria)
        
        if categorias_detectadas:
            logger.info(
                f"Categorías detectadas en '{pregunta}': {categorias_detectadas}"
            )
        else:
            logger.info(f"Consulta general detectada: '{pregunta}'")
        
        return categorias_detectadas
    
    def _detectar_rango_meses(self, pregunta: str) -> tuple[int, int, int, int] | None:
        """
        Detecta si la pregunta pide datos de un mes específico o rango de meses.
        Retorna (mes_inicio, anio_inicio, mes_fin, anio_fin) o None si es mes actual.

        Ejemplos:
            'gasto en octubre'       -> (10, año_actual, 10, año_actual)
            'últimos 3 meses'        -> (mes-2, año, mes_actual, año_actual)
            'mes pasado'             -> (mes-1, año, mes-1, año)
        """
        ahora = datetime.now()
        mes_actual = ahora.month
        anio_actual = ahora.year
        query = pregunta.lower()

        # Detectar mes nombrado explícitamente (ej: 'octubre', 'en marzo')
        for nombre, num in self._MESES_ES.items():
            if nombre in query:
                anio = anio_actual if num <= mes_actual else anio_actual - 1
                logger.info("[RANGO] Mes detectado: %s (%d/%d)", nombre, num, anio)
                return (num, anio, num, anio)

        # Detectar 'mes pasado' o 'el mes anterior'
        if re.search(r'mes\s+pasado|mes\s+anterior', query):
            mes = mes_actual - 1 if mes_actual > 1 else 12
            anio = anio_actual if mes_actual > 1 else anio_actual - 1
            logger.info("[RANGO] Mes pasado: %d/%d", mes, anio)
            return (mes, anio, mes, anio)

        # Detectar 'últimos N meses'
        m = re.search(r'[uú]ltimos?\s+(\d+)\s+meses?', query)
        if m:
            n = int(m.group(1))
            mes_ini = mes_actual - n + 1
            anio_ini = anio_actual
            while mes_ini < 1:
                mes_ini += 12
                anio_ini -= 1
            logger.info("[RANGO] Últimos %d meses: %d/%d -> %d/%d",
                        n, mes_ini, anio_ini, mes_actual, anio_actual)
            return (mes_ini, anio_ini, mes_actual, anio_actual)

        return None

    def _filtrar_gastos_por_contexto(
        self,
        gastos: list[Expense],
        categorias: list[str]
    ) -> list[Expense]:
        """
        Filtra gastos según las categorías detectadas.
        
        Args:
            gastos: Lista completa de gastos del mes
            categorias: Categorías detectadas (valores exactos con emojis)
            
        Returns:
            Gastos filtrados por categoría o últimos 10 si es consulta general
        """
        # Log de categorías reales en BD para debugging
        categorias_en_bd = set(g.categoria.value for g in gastos)
        logger.info(f"Categorías encontradas en BD: {categorias_en_bd}")
        
        if not categorias:
            # Consulta general: enviar TODOS los gastos del mes (sin límite arbitrario)
            # Antes se limitaba a 10, lo que ocultaba información al modelo.
            gastos_filtrados = gastos
            logger.info(
                f"Consulta general: enviando totalidad de {len(gastos_filtrados)} gastos del mes"
            )
            return gastos_filtrados
        
        # Consulta específica: TODOS los gastos de las categorías relevantes
        # Comparar con valores EXACTOS (con emojis)
        gastos_filtrados = [
            g for g in gastos
            if g.categoria.value in categorias
        ]
        
        logger.info(
            f"Filtrado por categorías {categorias}: "
            f"{len(gastos_filtrados)} gastos de {len(gastos)} totales"
        )
        
        # Si no encontró gastos, loggear para debugging
        if not gastos_filtrados and categorias:
            logger.warning(
                f"⚠️ No se encontraron gastos para categorías {categorias}. "
                f"Categorías disponibles: {categorias_en_bd}"
            )
        
        return gastos_filtrados
    
    def _agrupar_gastos(self, gastos: list[Expense]) -> dict:
        """
        Agrupa gastos por categoría y descripción para el analista financiero.
        
        Returns:
            {
                "Categoría": {
                    "Descripción": {"total": float, "cantidad": int, "metodos": dict}
                }
            }
        """
        resumen: dict[str, dict[str, dict]] = {}
        for gasto in gastos:
            cat = gasto.categoria.value
            desc = gasto.descripcion.strip().capitalize()
            metodo = gasto.metodo_pago.value
            
            if cat not in resumen:
                resumen[cat] = {}
            
            if desc not in resumen[cat]:
                resumen[cat][desc] = {"total": 0.0, "cantidad": 0, "metodos": {}}
            
            resumen[cat][desc]["total"] += gasto.monto
            resumen[cat][desc]["cantidad"] += 1
            metodos = resumen[cat][desc]["metodos"]
            metodos[metodo] = metodos.get(metodo, 0) + 1
            
        return resumen

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
            logger.warning("[SUBTOTAL] No se pudo generar embedding: %s", embedding_result.err())
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
            len(resultados), umbral_cosine, subtotal,
        )
        return subtotal, label

    def _resumir_metodos_pago(self, gastos: list[Expense]) -> str:
        """
        Genera un resumen de métodos de pago usados en el mes.
        
        Returns:
            String con el conteo por método de pago
        """
        conteo: dict[str, int] = {}
        for gasto in gastos:
            metodo = gasto.metodo_pago.value
            conteo[metodo] = conteo.get(metodo, 0) + 1
        
        total = sum(conteo.values())
        partes = [
            f"{metodo}: {cant} compras ({cant * 100 // total}%)"
            for metodo, cant in sorted(conteo.items(), key=lambda x: -x[1])
        ]
        return ", ".join(partes)

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

            rango = self._detectar_rango_meses(pregunta)
            if rango:
                mes_ini, anio_ini, mes_fin, anio_fin = rango
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
                    len(gastos_mes), mes_ini, anio_ini, mes_fin, anio_fin,
                )
            else:
                gastos_mes = [
                    g for g in expense_service.list_expenses()
                    if g.fecha.month == mes_actual and g.fecha.year == anio_actual
                ]

            categorias_relevantes = self._detectar_categorias_relevantes(pregunta)
            gastos_filtrados = self._filtrar_gastos_por_contexto(
                gastos_mes, categorias_relevantes
            )

            total_gastos_mes = sum(g.monto for g in gastos_mes)
            resumen_gastos: dict[str, dict[str, dict]] = {}
            total_gastos_count = 0
            if gastos_filtrados:
                resumen_gastos = self._agrupar_gastos(gastos_filtrados)
                total_gastos_count = len(gastos_filtrados)

            subtotal_desc, label_desc = await self._calcular_subtotal_semantico(
                pregunta, session
            )

            income_repo = IncomeRepository(session, self._familia_id)
            income_service = IncomeService(income_repo)
            ingresos = [
                i for i in income_service.list_incomes()
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
                resumen_metodos_pago=self._resumir_metodos_pago(gastos_mes),
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
        self,
        pregunta: str,
        incluir_gastos: bool = True
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
            incluir_gastos_recientes=incluir_gastos
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
