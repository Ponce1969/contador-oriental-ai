"""
Tests para ModelRouter — Decisión de modelo híbrido.

Criterio de aceptación:
- Keywords de normativa/fiscal → 'llama3' (si hay cuota)
- Keywords sin cuota → 'gemma2'
- from_history=True → 'llama3' (si hay cuota)
- from_history=True sin cuota → 'gemma2'
- Contexto con empalme → 'llama3' (si hay cuota)
- Consulta simple → 'gemma2'
- Todas las keywords están cubiertas
"""
from __future__ import annotations

import pytest

from models.ai_model import AIContext
from services.ai.model_router import KEYWORDS_LLAMA3, ModelRouter


@pytest.fixture
def router() -> ModelRouter:
    """ModelRouter para tests."""
    return ModelRouter()


@pytest.fixture
def ctx_empty() -> AIContext:
    """Contexto vacío — sin gastos, sin empalme."""
    return AIContext()


@pytest.fixture
def ctx_with_empalme() -> AIContext:
    """Contexto con empalme del mes anterior."""
    return AIContext(
        empalme_mes_label="Abril 2025",
        empalme_total_gastos=100000,
        empalme_ingresos_total=150000,
    )


class TestModelRouterKeywords:
    """Verifica que las keywords de normativa dirigen a Llama 3."""

    @pytest.mark.parametrize(
        "keyword",
        [
            "iva",
            "bps",
            "irpf",
            "dgi",
            "sucive",
            "patente",
            "inclusion financiera",
            "beneficio tarjeta",
            "deduccion",
            "exención",
            "retencion",
            "tributo",
            "impuesto",
            "proyeccion",
            "ahorro",
            "optimizar",
            "planificar",
            "3 meses",
            "historial",
            "ley",
            "decreto",
        ],
    )
    def test_keyword_routes_to_llama3(self, router: ModelRouter, keyword: str):
        """Cada keyword fiscal/legal debe dirigir a Llama 3 si hay cuota."""
        pregunta = f"¿Cuál es el {keyword} que me corresponde?"
        assert router.route(pregunta, has_quota=True) == "llama3"

    @pytest.mark.parametrize(
        "keyword",
        ["iva", "bps", "irpf", "dgi", "patente", "impuesto"],
    )
    def test_keyword_sin_cuota_routes_to_gemma2(
        self, router: ModelRouter, keyword: str
    ):
        """Sin cuota, las keywords caen a Gemma 2."""
        pregunta = f"¿Cuál es el {keyword} que me corresponde?"
        assert router.route(pregunta, has_quota=False) == "gemma2"


class TestModelRouterHistory:
    """Verifica el routing desde el botón de Historial."""

    def test_from_history_with_quota(self, router: ModelRouter):
        """Viene del Historial con cuota → Llama 3."""
        assert (
            router.route(
                "Resumen de gastos de los últimos 3 meses",
                from_history=True,
                has_quota=True,
            )
            == "llama3"
        )

    def test_from_history_without_quota(self, router: ModelRouter):
        """Viene del Historial sin cuota → Gemma 2."""
        assert (
            router.route(
                "Resumen de gastos de los últimos 3 meses",
                from_history=True,
                has_quota=False,
            )
            == "gemma2"
        )


class TestModelRouterEmpalme:
    """Verifica el routing cuando hay contexto de empalme."""

    def test_empalme_with_quota(self, router: ModelRouter, ctx_with_empalme):
        """Contexto con empalme y cuota → Llama 3."""
        assert (
            router.route(
                "¿Cómo van mis gastos?",
                ctx=ctx_with_empalme,
                has_quota=True,
            )
            == "llama3"
        )

    def test_empalme_without_quota(self, router: ModelRouter, ctx_with_empalme):
        """Contexto con empalme sin cuota → Gemma 2."""
        assert (
            router.route(
                "¿Cómo van mis gastos?",
                ctx=ctx_with_empalme,
                has_quota=False,
            )
            == "gemma2"
        )

    def test_empty_context_simple_question(self, router: ModelRouter, ctx_empty):
        """Contexto vacío con pregunta simple → Gemma 2."""
        assert (
            router.route(
                "¿Cuánto gasté en supermercado?",
                ctx=ctx_empty,
                has_quota=True,
            )
            == "gemma2"
        )


class TestModelRouterDefaults:
    """Verifica defaults y edge cases."""

    def test_simple_question_default_gemma2(self, router: ModelRouter):
        """Pregunta simple sin keywords → Gemma 2."
        """
        assert router.route("¿Cuánto gasté hoy?", has_quota=True) == "gemma2"

    def test_empty_question_gemma2(self, router: ModelRouter):
        """Pregunta vacía → Gemma 2."""
        assert router.route("", has_quota=True) == "gemma2"

    def test_no_context_gemma2(self, router: ModelRouter):
        """Sin contexto y pregunta simple → Gemma 2."""
        assert router.route("hola", has_quota=True) == "gemma2"

    def test_case_insensitive_keywords(self, router: ModelRouter):
        """Keywords son case-insensitive."""
        assert router.route("¿Qué es el IVA?", has_quota=True) == "llama3"
        assert router.route("¿qué es el iva?", has_quota=True) == "llama3"


class TestModelRouterKeywordsCompleteness:
    """Verifica que KEYWORDS_LLAMA3 tiene las keywords esperadas."""

    def test_all_expected_keywords_present(self):
        """Las keywords críticas deben estar en el frozenset."""
        expected = {
            "iva",
            "bps",
            "irpf",
            "dgi",
            "sucive",
            "patente",
            "proyeccion",
            "ahorro",
            "historial",
            "3 meses",
            "ley",
        }
        assert expected.issubset(KEYWORDS_LLAMA3), (
            f"Keys faltantes: {expected - KEYWORDS_LLAMA3}"
        )