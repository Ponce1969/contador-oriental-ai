"""
Tests de invariantes para el submotor de Pequeña Empresa - Literal E (Fase 3B).
Valida conversión a UI (tope 305.000 UI), cuota DGI (25%/50%/100%) y BPS.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from services.labor.calculations.independent.literal_e import (
    calculate_activity_months,
    calculate_literal_e_settlement,
)
from services.labor.domain.dtos import IndependentProfile
from services.labor.domain.enums import (
    CalculationStatus,
    EligibilityStatus,
    IndependentTaxRegime,
)
from services.labor.domain.tax_rules import (
    get_literal_e_ruleset,
    get_ui_value,
)
from services.labor.engine import LaborCalculationEngine


class TestLiteralEEligibilityAndUIConversion:
    """Verifica la evaluación del tope de 305.000 UI con conversión dinámica."""

    def test_ventas_dentro_del_tope_es_elegible(self):
        """Ventas de $1.500.000 UYU están por debajo de 305.000 UI (~$1.958.100)."""
        rules = get_literal_e_ruleset(2026)
        ui_val = get_ui_value(2026)
        assert rules is not None and ui_val is not None

        profile = IndependentProfile(
            regime=IndependentTaxRegime.LITERAL_E,
            regime_start_date=date(2025, 1, 1),
        )

        res = calculate_literal_e_settlement(
            annual_gross_sales_uyu=Decimal("1500000.00"),
            profile=profile,
            rules=rules,
            ui_value=ui_val,
            calculation_date=date(2026, 6, 1),
        )

        assert res.eligibility is not None
        assert res.eligibility.status == EligibilityStatus.ELIGIBLE
        assert res.eligibility.can_proceed_to_calculation is True
        assert res.literal_e_payload is not None
        assert res.literal_e_payload.annual_gross_sales_ui < Decimal("305000.00")

    def test_ventas_superan_tope_excluye_preceptivamente(self):
        """Ventas de $2.500.000 UYU superan 305.000 UI y excluyen de Literal E."""
        rules = get_literal_e_ruleset(2026)
        ui_val = get_ui_value(2026)
        assert rules is not None and ui_val is not None

        profile = IndependentProfile(
            regime=IndependentTaxRegime.LITERAL_E,
            regime_start_date=date(2025, 1, 1),
        )

        res = calculate_literal_e_settlement(
            annual_gross_sales_uyu=Decimal("2500000.00"),
            profile=profile,
            rules=rules,
            ui_value=ui_val,
            calculation_date=date(2026, 6, 1),
        )

        assert res.eligibility is not None
        assert res.eligibility.status == EligibilityStatus.INELIGIBLE
        assert not res.eligibility.can_proceed_to_calculation
        assert any("superan tope" in v for v in res.eligibility.violations)


class TestLiteralEStepUpFees:
    """Verifica el escalonamiento de la cuota mensual DGI según antigüedad."""

    def test_ano_1_bonificacion_25_porciento(self):
        """Mes 6 de actividad: paga el 25% de la cuota base DGI + BPS patronal."""
        rules = get_literal_e_ruleset(2026)
        ui_val = get_ui_value(2026)
        assert rules is not None and ui_val is not None

        profile = IndependentProfile(
            regime=IndependentTaxRegime.LITERAL_E,
            regime_start_date=date(2026, 1, 1),
        )

        res = calculate_literal_e_settlement(
            annual_gross_sales_uyu=Decimal("1000000.00"),
            profile=profile,
            rules=rules,
            ui_value=ui_val,
            calculation_date=date(2026, 6, 1),  # Mes 6
        )

        payload = res.literal_e_payload
        assert payload is not None
        assert payload.activity_months_age == 6
        assert payload.dgi_discount_rate_applied == Decimal("0.2500")

        # Base DGI $5.450 * 25% = $1.362,50
        assert payload.dgi_monthly_fee == Decimal("1362.50")
        assert payload.bps_patronal_monthly_fee == Decimal("4200.00")
        assert payload.total_monthly_obligations == Decimal("5562.50")

    def test_ano_2_bonificacion_50_porciento(self):
        """Mes 18 de actividad: paga el 50% de la cuota base DGI + BPS patronal."""
        rules = get_literal_e_ruleset(2026)
        ui_val = get_ui_value(2026)
        assert rules is not None and ui_val is not None

        profile = IndependentProfile(
            regime=IndependentTaxRegime.LITERAL_E,
            regime_start_date=date(2025, 1, 1),
        )

        res = calculate_literal_e_settlement(
            annual_gross_sales_uyu=Decimal("1000000.00"),
            profile=profile,
            rules=rules,
            ui_value=ui_val,
            calculation_date=date(2026, 6, 1),  # Mes 18
        )

        payload = res.literal_e_payload
        assert payload is not None
        assert payload.activity_months_age == 18
        assert payload.dgi_discount_rate_applied == Decimal("0.5000")

        # Base DGI $5.450 * 50% = $2.725,00
        assert payload.dgi_monthly_fee == Decimal("2725.00")
        assert payload.total_monthly_obligations == Decimal("6925.00")

    def test_ano_3_mas_cuota_plena_100_porciento(self):
        """Mes 30 de actividad: paga el 100% de la cuota base DGI + BPS patronal."""
        rules = get_literal_e_ruleset(2026)
        ui_val = get_ui_value(2026)
        assert rules is not None and ui_val is not None

        profile = IndependentProfile(
            regime=IndependentTaxRegime.LITERAL_E,
            regime_start_date=date(2023, 12, 1),
        )

        res = calculate_literal_e_settlement(
            annual_gross_sales_uyu=Decimal("1000000.00"),
            profile=profile,
            rules=rules,
            ui_value=ui_val,
            calculation_date=date(2026, 6, 1),  # Mes 31
        )

        payload = res.literal_e_payload
        assert payload is not None
        assert payload.dgi_discount_rate_applied == Decimal("1.0000")

        # Base DGI $5.450 * 100% = $5.450,00
        assert payload.dgi_monthly_fee == Decimal("5450.00")
        assert payload.total_monthly_obligations == Decimal("9650.00")


class TestLiteralEBoundariesAndOrchestration:
    """Verifica casos de frontera de meses y orquestación del engine."""

    def test_fronteras_de_meses_12_a_13_y_24_a_25(self):
        """Valida que la función calculate_activity_months incremente mes a mes."""
        start = date(2025, 1, 1)

        assert calculate_activity_months(start, date(2025, 12, 1)) == 12
        assert calculate_activity_months(start, date(2026, 1, 1)) == 13
        assert calculate_activity_months(start, date(2026, 12, 1)) == 24
        assert calculate_activity_months(start, date(2027, 1, 1)) == 25

    def test_orquestacion_engine_literal_e(self):
        """Prueba calculate_literal_e a través de LaborCalculationEngine."""
        profile = IndependentProfile(
            regime=IndependentTaxRegime.LITERAL_E,
            regime_start_date=date(2026, 1, 1),
        )

        result = LaborCalculationEngine.calculate_literal_e(
            annual_gross_sales_uyu=Decimal("1200000.00"),
            profile=profile,
            fiscal_year=2026,
            calculation_date=date(2026, 6, 1),
        )

        assert result.status == CalculationStatus.CALCULATED
        assert result.literal_e_payload is not None
        assert result.literal_e_payload.dgi_monthly_fee == Decimal("1362.50")
        assert result.total_withholdings == Decimal("5562.50")
