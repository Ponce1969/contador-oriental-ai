"""Controlador para el Contador Oriental"""

from __future__ import annotations

import difflib
import logging
import re
from collections.abc import Generator
from contextlib import contextmanager

from result import Result
from sqlalchemy.orm import Session

from core.sqlalchemy_session import get_db_session
from models.ai_model import AIRequest, AIResponse
from models.errors import AppError
from models.expense_model import Expense
from repositories.expense_repository import ExpenseRepository
from repositories.family_member_repository import FamilyMemberRepository
from repositories.income_repository import IncomeRepository
from services.ai_advisor_service import AIAdvisorService
from services.expense_service import ExpenseService
from services.family_member_service import FamilyMemberService
from services.income_service import IncomeService

logger = logging.getLogger(__name__)


class AIController:
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
        self.familia_id = familia_id
        self.ai_service = AIAdvisorService()
    
    @contextmanager
    def _get_session(self) -> Generator[Session, None, None]:
        """Obtener sesión de base de datos."""
        with get_db_session() as session:
            yield session
    
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
    
    def consultar_contador(
        self,
        pregunta: str,
        incluir_gastos: bool = True
    ) -> Result[AIResponse, AppError]:
        """
        Consulta al Contador Oriental con detección inteligente de contexto.
        
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
            familia_id=self.familia_id,
            incluir_gastos_recientes=incluir_gastos
        )
        
        # Obtener datos financieros y familiares si se solicita
        gastos_filtrados: list[Expense] | None = None
        ingresos_total = 0.0
        miembros_count = 0
        
        if incluir_gastos:
            with self._get_session() as session:
                from datetime import datetime
                
                # Obtener gastos del mes actual
                expense_repo = ExpenseRepository(session, self.familia_id)
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
                
                # Obtener ingresos del mes actual
                income_repo = IncomeRepository(session, self.familia_id)
                income_service = IncomeService(income_repo)
                ingresos = income_service.list_incomes()
                ingresos = [
                    i for i in ingresos
                    if i.fecha.month == mes_actual and i.fecha.year == anio_actual
                ]
                ingresos_total = sum(i.monto for i in ingresos)
                
                # Obtener miembros de la familia
                member_repo = FamilyMemberRepository(session, self.familia_id)
                member_service = FamilyMemberService(member_repo)
                miembros = member_service.list_members()
                miembros_count = len(miembros)
        
        # Consultar al servicio de IA con gastos filtrados
        return self.ai_service.consultar(
            request, gastos_filtrados, ingresos_total, miembros_count
        )
    
    def get_title(self) -> str:
        """Título de la vista"""
        return "🧮 Contador Oriental"
    
    def get_description(self) -> str:
        """Descripción del servicio"""
        return "Asistente contable con IA para familias uruguayas"
