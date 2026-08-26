"""
Tests de integración para la conexión del Asesor de IA con perfiles laborales.
Verifica que las métricas pre-calculadas por Python (retención IRPF, Montepío,
Fonasa, Líquido en mano, Aguinaldo) se inyecten de forma determinística.
"""

from decimal import Decimal

from models.ai_model import AIContext
from services.ai.ai_advisor_service import AIAdvisorService
from services.labor.domain.enums import FonasaBeneficiaryType
from services.labor.domain.models import TaxProfile
from services.labor.engine import LaborCalculationEngine


def test_ai_advisor_labor_context_injection():
    """
    Verifica que el AIAdvisorService reciba el bloque contextual de beneficios
    laborales pre-calculados y lo incluya en el prompt sin recálculos.
    """
    svc = AIAdvisorService()

    resumen_laboral_mock = "\n".join(
        [
            "- Integrante: Carlos | Actividad: Empleado de Comercio (dependiente)",
            "  * Sueldo Nominal Mensual: $ 80000.00",
            "  * Aporte Jubilatorio Montepío (15%): $ 12000.00",
            "  * Fondo Reconversión Laboral (0.1%): $ 80.00",
            "  * Seguro FONASA (6.0%): $ 4800.00",
            "  * Retención IRPF Anticipo Mensual (10% marg.): $ 2450.00",
            "  * Líquido Estimado en Mano: $ 60670.00",
        ]
    )

    ctx = AIContext(
        resumen_gastos={},
        total_gastos_count=0,
        total_gastos_mes=Decimal("0"),
        ingresos_total=Decimal("80000"),
        miembros_count=1,
        resumen_metodos_pago="",
        comparativa_meses=[],
        resumen_laboral=resumen_laboral_mock,
        periodo_label="de Agosto 2026",
    )

    gastos_fmt = svc._formatear_datos_financieros(ctx)
    prompt = svc._construir_prompt(
        pregunta="¿Cuánto me van a retener de IRPF este mes?",
        contexto_legal="",
        gastos_formateados=gastos_fmt,
        modelo="gemma2",
        ctx=ctx,
    )

    # Verificaciones de inyección estricta
    assert (
        "### CONTEXTO, SUELDOS Y BENEFICIOS LABORALES DEL HOGAR "
        "(PRE-CALCULADO POR PYTHON) ###" in prompt
    )
    assert "Sueldo Nominal Mensual: $ 80000.00" in prompt
    assert "Retención IRPF Anticipo Mensual (10% marg.): $ 2450.00" in prompt
    assert "Líquido Estimado en Mano: $ 60670.00" in prompt
    assert "NUNCA inventes cálculos ni discrepes" in prompt


def test_labor_engine_withholdings_integration():
    """
    Verifica que el LaborCalculationEngine produzca las métricas exactas
    para un dependiente con perfil familiar (hijos y cónyuge).
    """
    tax_profile = TaxProfile(
        children_count=2,
        has_spouse_charge=True,
        fonasa_type=FonasaBeneficiaryType.WITH_CHILDREN_AND_SPOUSE,
    )
    result = LaborCalculationEngine.calculate_withholdings(
        nominal=Decimal("120000.00"),
        profile=tax_profile,
        fiscal_year=2026,
    )

    assert result.nominal_amount == Decimal("120000.00")
    assert result.montepio_amount == Decimal("18000.00")  # 15%
    assert result.frl_amount == Decimal("120.00")  # 0.1%
    assert result.fonasa_amount > Decimal("0.00")
    assert result.irpf_net_withholding > Decimal("0.00")
    assert result.liquid_amount == (
        result.nominal_amount
        - result.montepio_amount
        - result.frl_amount
        - result.fonasa_amount
        - result.irpf_net_withholding
    )
