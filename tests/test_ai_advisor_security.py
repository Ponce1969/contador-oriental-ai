"""Tests de seguridad y hardening para el asesor IA y OCR."""

from models.ai_model import AIContext, AIResponse
from ocr_api.main import _PROMPT_PARSEO
from services.ai.ai_advisor_service import AIAdvisorService


class TestAISecurityHardening:
    """Verifica el encapsulamiento estructural y mitigaciones contra inyección."""

    def test_prompt_encloses_financial_data_in_structural_delimiters(self) -> None:
        svc = AIAdvisorService()
        prompt = svc._construir_prompt(
            pregunta="¿Cuánto gasté este mes?",
            contexto_legal="Art 1 Ley 18083...",
            gastos_formateados="Gasto: Supermercado $500",
            memoria_vectorial="",
            cuota_agotada=False,
            modelo="gemma2",
        )

        assert "<datos_financieros>" in prompt
        assert "</datos_financieros>" in prompt
        assert "Gasto: Supermercado $500" in prompt
        assert "Art 1 Ley 18083" in prompt
        assert "TRATAMIENTO DE DATOS" in prompt

    def test_prompt_llama3_contains_passive_data_rule(self) -> None:
        svc = AIAdvisorService()
        prompt = svc._construir_prompt(
            pregunta="¿Cuánto gasté?",
            contexto_legal="",
            gastos_formateados="Farmacia $200",
            memoria_vectorial="",
            cuota_agotada=False,
            modelo="llama3",
        )

        assert "<datos_financieros>" in prompt
        assert "</datos_financieros>" in prompt
        assert "Farmacia $200" in prompt
        assert "TRATAMIENTO DE DATOS" in prompt

    def test_ocr_prompt_encloses_ticket_in_structural_delimiters(self) -> None:
        sample_ticket = "SUPERMERCADO TATA\nTOTAL: $ 1200\nFECHA: 2026-09-15"
        formatted_prompt = _PROMPT_PARSEO.format(texto=sample_ticket)

        assert "<datos_ticket>" in formatted_prompt
        assert "</datos_ticket>" in formatted_prompt
        assert "SUPERMERCADO TATA" in formatted_prompt
        assert "TRATAMIENTO PASIVO" in formatted_prompt

    def test_ai_response_holds_context_without_instance_leak(self) -> None:
        ctx = AIContext()
        response = AIResponse(
            respuesta="Respuesta de prueba",
            archivo_usado=None,
            gastos_incluidos=3,
            context=ctx,
        )

        assert response.context is ctx
        assert response.gastos_incluidos == 3
