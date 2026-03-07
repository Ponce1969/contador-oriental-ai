"""
QueryAnalyzer — Analizador de lenguaje natural para consultas financieras.
Lógica NLU pura: sin BD, sin async, sin estado. Determinístico y testeable.
"""
from __future__ import annotations

import difflib
import logging
import re
from datetime import datetime
from typing import NamedTuple

logger = logging.getLogger(__name__)


class IntentData(NamedTuple):
    """Resultado del análisis de intención de una pregunta."""
    categorias: list[str]
    rango: tuple[int, int, int, int] | None


_PALABRAS_TEMPORALES: frozenset[str] = frozenset([
    "pasado", "pasada", "anterior", "anteriores", "previo", "previa",
    "ultimo", "última", "ultimos", "últimas", "actual", "reciente",
    "meses", "semana", "semanas", "dias", "años", "año",
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    "cuanto", "cuánto", "cual", "cuál", "como", "cómo", "cuando", "cuándo",
    "gaste", "gasté", "total", "resumen", "gasto", "gastos",
])

_MESES_ES: dict[str, int] = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "🛒 Almacén": [
        "super", "supermercado", "comida", "almacen", "almacén",
        "compras", "comestibles", "mercado", "verduleria", "verdulería",
        "carniceria", "carnicería", "panaderia", "panadería", "delivery",
    ],
    "🚗 Vehículos": [
        "nafta", "combustible", "gasolina", "auto", "coche", "vehiculo",
        "vehículo", "transporte", "peaje", "estacionamiento", "patente",
        "seguro auto", "mantenimiento auto",
    ],
    "🏠 Hogar": [
        "luz", "agua", "gas", "internet", "telefono", "teléfono",
        "cable", "alquiler", "casa", "hogar", "expensas", "servicio",
    ],
    "👨‍⚕️ Salud": [
        "farmacia", "medico", "médico", "doctor", "hospital",
        "clinica", "clínica", "medicamento", "salud", "consulta",
        "obra social", "odontologo", "odontólogo",
    ],
    "🎉 Ocio": [
        "cine", "teatro", "salida", "restaurante", "cena",
        "asado", "bar", "cerveza", "entretenimiento", "ocio",
        "vacaciones", "paseo", "streaming", "netflix", "spotify",
    ],
    "📚 Educación": [
        "escuela", "colegio", "universidad", "curso", "libro",
        "material", "educacion", "educación", "estudio", "utiles", "útiles",
    ],
    "👕 Ropa": [
        "ropa", "vestimenta", "calzado", "zapato", "remera",
        "pantalon", "pantalón", "campera", "abrigo", "zapatilla",
    ],
    "💳 Otros": [
        "impuesto", "seguro", "prestamo", "préstamo", "varios",
    ],
}


class QueryAnalyzer:
    """
    Analizador de lenguaje natural para consultas financieras uruguayas.
    Métodos de clase — no requiere instancia ni estado.
    """

    @classmethod
    def detectar_intenciones(cls, pregunta: str) -> IntentData:
        """
        Orquesta la detección de categorías y rango temporal.
        Punto de entrada principal: el AIController solo llama este método.
        """
        categorias = cls.detectar_categorias(pregunta)
        rango = cls.detectar_rango_meses(pregunta)
        return IntentData(categorias=categorias, rango=rango)

    @classmethod
    def detectar_categorias(cls, pregunta: str) -> list[str]:
        """
        Detecta categorías financieras en la pregunta con fuzzy matching.
        Excluye palabras temporales/comunes para evitar falsos positivos.
        """
        query_lower = pregunta.lower()
        palabras = re.findall(r"\w+", query_lower)
        detectadas: list[str] = []

        for categoria, keywords in CATEGORY_KEYWORDS.items():
            match_encontrado = False
            for keyword in keywords:
                if " " in keyword:
                    if keyword in query_lower:
                        match_encontrado = True
                        break
                else:
                    if keyword in palabras:
                        match_encontrado = True
                        break
                    candidatos = [
                        p for p in palabras if p not in _PALABRAS_TEMPORALES
                    ]
                    matches = difflib.get_close_matches(
                        keyword, candidatos, n=1, cutoff=0.88
                    )
                    if matches:
                        logger.info(
                            "Fuzzy match: '%s' -> '%s' (%s)",
                            matches[0], keyword, categoria,
                        )
                        match_encontrado = True
                        break
            if match_encontrado:
                detectadas.append(categoria)

        if detectadas:
            logger.info("Categorías detectadas en '%s': %s", pregunta, detectadas)
        else:
            logger.info("Consulta general detectada: '%s'", pregunta)

        return detectadas

    @classmethod
    def detectar_rango_meses(cls, pregunta: str) -> tuple[int, int, int, int] | None:
        """
        Detecta si la pregunta pide datos de un mes específico o rango.
        Retorna (mes_ini, anio_ini, mes_fin, anio_fin) o None si es mes actual.

        Ejemplos:
            'gasto en octubre'    -> (10, año_actual, 10, año_actual)
            'últimos 3 meses'     -> (mes-2, año, mes_actual, año_actual)
            'mes pasado'          -> (mes-1, año, mes-1, año)
        """
        ahora = datetime.now()
        mes_actual = ahora.month
        anio_actual = ahora.year
        query = pregunta.lower()

        for nombre, num in _MESES_ES.items():
            if nombre in query:
                anio = anio_actual if num <= mes_actual else anio_actual - 1
                logger.info("[RANGO] Mes detectado: %s (%d/%d)", nombre, num, anio)
                return (num, anio, num, anio)

        if re.search(r"mes\s+pasado|mes\s+anterior", query):
            mes = mes_actual - 1 if mes_actual > 1 else 12
            anio = anio_actual if mes_actual > 1 else anio_actual - 1
            logger.info("[RANGO] Mes pasado: %d/%d", mes, anio)
            return (mes, anio, mes, anio)

        m = re.search(r"[uú]ltimos?\s+(\d+)\s+meses?", query)
        if m:
            n = int(m.group(1))
            mes_ini = mes_actual - n + 1
            anio_ini = anio_actual
            while mes_ini < 1:
                mes_ini += 12
                anio_ini -= 1
            logger.info(
                "[RANGO] Últimos %d meses: %d/%d -> %d/%d",
                n, mes_ini, anio_ini, mes_actual, anio_actual,
            )
            return (mes_ini, anio_ini, mes_actual, anio_actual)

        return None
