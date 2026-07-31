"""Tests para el system prompt del asesor IA."""

from services.ai.ai_advisor_service import AIAdvisorService


class TestAIPrompt:
    def test_prompt_rejects_old_rules_and_adds_per_currency_guidance(self):
        svc = AIAdvisorService()
        prompt = svc._construir_prompt(
            pregunta="test",
            contexto_legal="",
            gastos_formateados="",
            memoria_vectorial="",
            cuota_agotada=False,
            modelo="gemma2",
        )
        assert "total mensual SIEMPRE en $" not in prompt
        assert "USD solo para contextualizar" not in prompt
        assert "NUNCA hacer cálculos" in prompt
        assert "Reportá cada moneda por separado" in prompt
        assert "NUNCA conviertas ni sumes monedas distintas" in prompt
