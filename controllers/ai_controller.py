"""Controlador para el Contador Oriental"""

from __future__ import annotations

import difflib
import logging
import re

from result import Result

from controllers.base_controller import BaseController
from models.ai_model import AIContext, AIRequest, AIResponse
from models.errors import AppError
from models.expense_model import Expense
from repositories.expense_repository import ExpenseRepository
from repositories.family_member_repository import FamilyMemberRepository
from repositories.income_repository import IncomeRepository
from repositories.monthly_snapshot_repository import MonthlySnapshotRepository
from services.ai_advisor_service import AIAdvisorService
from services.expense_service import ExpenseService
from services.family_member_service import FamilyMemberService
from services.income_service import IncomeService

logger = logging.getLogger(__name__)


class AIController(BaseController):
    """Controlador para interactuar con el Contador Oriental"""
    
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
        self.last_context: AIContext = AIContext()
        self.last_pregunta: str = ""
    
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
                    
                    # Fuzzy matching (typos)
                    # cutoff=0.8 permite pequeños errores (ej: alamcen -> almacen)
                    matches = difflib.get_close_matches(
                        keyword, palabras_pregunta, n=1, cutoff=0.8
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
        
        # Obtener datos financieros y familiares si se solicita
        gastos_filtrados: list[Expense] | None = None
        ctx = AIContext()
        
        if incluir_gastos:
            with self._get_session() as session:
                from datetime import datetime
                
                # Obtener gastos del mes actual
                expense_repo = ExpenseRepository(session, self._familia_id)
                expense_service = ExpenseService(expense_repo)
                gastos_mes = expense_service.list_expenses()
                
                # Filtrar por mes actual
                mes_actual = datetime.now().month
                anio_actual = datetime.now().year
                gastos_mes = [
                    g for g in gastos_mes
                    if g.fecha.month == mes_actual and g.fecha.year == anio_actual
                ]
                
                logger.info(f"Gastos del mes actual: {len(gastos_mes)}")
                
                # Detección inteligente de intención
                categorias_relevantes = self._detectar_categorias_relevantes(
                    pregunta
                )
                
                # Filtrado contextual de gastos
                gastos_filtrados = self._filtrar_gastos_por_contexto(
                    gastos_mes, categorias_relevantes
                )
                
                # Total real del mes (TODOS los gastos, sin filtrar por categoría)
                total_gastos_mes = sum(g.monto for g in gastos_mes)
                
                # Agregación para el Analista Financiero
                resumen_gastos: dict = {}
                total_gastos_count = 0
                if gastos_filtrados:
                    resumen_gastos = self._agrupar_gastos(gastos_filtrados)
                    total_gastos_count = len(gastos_filtrados)
                
                # Obtener ingresos del mes actual
                income_repo = IncomeRepository(session, self._familia_id)
                income_service = IncomeService(income_repo)
                ingresos = income_service.list_incomes()
                ingresos = [
                    i for i in ingresos
                    if i.fecha.month == mes_actual and i.fecha.year == anio_actual
                ]
                ingresos_total = sum(i.monto for i in ingresos)
                
                # Obtener miembros de la familia
                member_repo = FamilyMemberRepository(session, self._familia_id)
                member_service = FamilyMemberService(member_repo)
                miembros = member_service.list_members()
                
                # Upsert snapshot del mes actual y obtener comparativa
                snapshot_repo = MonthlySnapshotRepository(session, self._familia_id)
                comparativa = []
                try:
                    snapshot_repo.upsert_mes_actual(anio_actual, mes_actual)
                    comparativa = snapshot_repo.obtener_comparativa_mensual(
                        anio_actual, mes_actual
                    )
                except Exception as snap_err:
                    logger.warning("No se pudo obtener comparativa mensual: %s", snap_err)

                ctx = AIContext(
                    resumen_gastos=resumen_gastos,
                    total_gastos_count=total_gastos_count,
                    total_gastos_mes=total_gastos_mes,
                    ingresos_total=ingresos_total,
                    miembros_count=len(miembros),
                    resumen_metodos_pago=self._resumir_metodos_pago(gastos_mes),
                    comparativa_meses=comparativa,
                )
        
        # Guardar contexto para exportación PDF
        self.last_context = ctx
        self.last_pregunta = pregunta

        # Consultar al servicio de IA (await = no bloquea el event loop)
        return await self.ai_service.consultar(request, ctx=ctx)

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
            with self._get_session() as session:
                from datetime import datetime

                expense_repo = ExpenseRepository(session, self._familia_id)
                expense_service = ExpenseService(expense_repo)
                gastos_mes = expense_service.list_expenses()

                mes_actual = datetime.now().month
                anio_actual = datetime.now().year
                gastos_mes = [
                    g for g in gastos_mes
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

                income_repo = IncomeRepository(session, self._familia_id)
                income_service = IncomeService(income_repo)
                ingresos = income_service.list_incomes()
                ingresos = [
                    i for i in ingresos
                    if i.fecha.month == mes_actual and i.fecha.year == anio_actual
                ]
                ingresos_total = sum(i.monto for i in ingresos)

                member_repo = FamilyMemberRepository(session, self._familia_id)
                member_service = FamilyMemberService(member_repo)
                miembros = member_service.list_members()

                snapshot_repo = MonthlySnapshotRepository(session, self._familia_id)
                comparativa = []
                try:
                    snapshot_repo.upsert_mes_actual(anio_actual, mes_actual)
                    comparativa = snapshot_repo.obtener_comparativa_mensual(
                        anio_actual, mes_actual
                    )
                except Exception as snap_err:
                    logger.warning("Comparativa no disponible: %s", snap_err)

                ctx = AIContext(
                    resumen_gastos=resumen_gastos,
                    total_gastos_count=total_gastos_count,
                    total_gastos_mes=total_gastos_mes,
                    ingresos_total=ingresos_total,
                    miembros_count=len(miembros),
                    resumen_metodos_pago=self._resumir_metodos_pago(gastos_mes),
                    comparativa_meses=comparativa,
                )

        self.last_context = ctx
        self.last_pregunta = pregunta

        async for token in self.ai_service.consultar_stream(request, ctx=ctx):
            yield token
    
    def get_title(self) -> str:
        """Título de la vista"""
        return "🧮 Contador Oriental"
    
    def get_description(self) -> str:
        """Descripción del servicio"""
        return "Asistente contable con IA para familias uruguayas"
