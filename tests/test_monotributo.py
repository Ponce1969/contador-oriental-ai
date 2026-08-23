"""
Tests de invariantes para Monotributo Común y Social MIDES (Fase 3C).
Valida elegibilidad (15 m2, 1 dependiente, topes UI), subsidio MIDES y cuota única.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from services.labor.calculations.independent.monotributo import (
    calculate_monotributo_settlement,
)
from services.labor.domain.dtos import IndependentProfile
from services.labor.domain.enums import (
    CalculationStatus,
    EligibilityStatus,
    IndependentTaxRegime,
)
from services.labor.domain.tax_rules import (
    get_monotributo_ruleset,
    get_ui_value,
)
from services.labor.engine import LaborCalculationEngine


class TestMonotributoEligibility:
    """Verifica reglas de elegibilidad física, de personal y de facturación."""

    def test_unipersonal_dentro_de_parametros_es_elegible(self):
        """Unipersonal con local de 10 m2 y ventas dentro de 183.000 UI es elegible."""
        rules = get_monotributo_ruleset(2026)
        ui_val = get_ui_value(2026)
        assert rules is not None and ui_val is not None

        profile = IndependentProfile(
            regime=IndependentTaxRegime.MONOTRIBUTO,
            local_premises_sqm=Decimal("10.00"),
            employees_count=1,
            regime_start_date=date(2025, 1, 1),
        )

        res = calculate_monotributo_settlement(
            annual_gross_sales_uyu=Decimal("800000.00"),
            profile=profile,
            rules=rules,
            ui_value=ui_val,
            calculation_date=date(2026, 6, 1),
        )

        assert res.eligibility is not None
        assert res.eligibility.status == EligibilityStatus.ELIGIBLE
        assert res.eligibility.can_proceed_to_calculation is True
        assert res.monotributo_payload is not None
        assert res.monotributo_payload.final_monthly_monotributo_fee == Decimal(
            "2850.00"
        )

    def test_local_supera_15_metros_es_inelegible(self):
        """Local comercial mayor a 15 m2 viola el límite legal de Monotributo."""
        rules = get_monotributo_ruleset(2026)
        ui_val = get_ui_value(2026)
        assert rules is not None and ui_val is not None

        profile = IndependentProfile(
            regime=IndependentTaxRegime.MONOTRIBUTO,
            local_premises_sqm=Decimal("25.00"),
            employees_count=0,
        )

        res = calculate_monotributo_settlement(
            annual_gross_sales_uyu=Decimal("500000.00"),
            profile=profile,
            rules=rules,
            ui_value=ui_val,
        )

        assert res.eligibility is not None
        assert res.eligibility.status == EligibilityStatus.INELIGIBLE
        assert not res.eligibility.can_proceed_to_calculation
        assert any("supera límite 15.00 m2" in v for v in res.eligibility.violations)

    def test_mas_de_un_dependiente_es_inelegible(self):
        """Tener 2 o más dependientes excluye de Monotributo."""
        rules = get_monotributo_ruleset(2026)
        ui_val = get_ui_value(2026)
        assert rules is not None and ui_val is not None

        profile = IndependentProfile(
            regime=IndependentTaxRegime.MONOTRIBUTO,
            local_premises_sqm=Decimal("12.00"),
            employees_count=2,
        )

        res = calculate_monotributo_settlement(
            annual_gross_sales_uyu=Decimal("500000.00"),
            profile=profile,
            rules=rules,
            ui_value=ui_val,
        )

        assert res.eligibility is not None
        assert res.eligibility.status == EligibilityStatus.INELIGIBLE
        assert any(
            "supera límite de 1 dependiente" in v for v in res.eligibility.violations
        )


class TestMonotributoSocialMIDES:
    """Verifica el subsidio escalonado en 4 años del Monotributo Social MIDES."""

    def test_mides_ano_1_bonificacion_25_porciento(self):
        """Año 1 MIDES: Paga el 25% de la cuota ($712,50)."""
        rules = get_monotributo_ruleset(2026)
        ui_val = get_ui_value(2026)
        assert rules is not None and ui_val is not None

        profile = IndependentProfile(
            regime=IndependentTaxRegime.MONOTRIBUTO_MIDES,
            has_mides_certificate=True,
            mides_certificate_expiry=date(2027, 1, 1),
            regime_start_date=date(2026, 1, 1),
        )

        res = calculate_monotributo_settlement(
            annual_gross_sales_uyu=Decimal("300000.00"),
            profile=profile,
            rules=rules,
            ui_value=ui_val,
            calculation_date=date(2026, 6, 1),  # Mes 6
        )

        payload = res.monotributo_payload
        assert payload is not None
        assert payload.is_mides_regime is True
        assert payload.mides_subsidy_rate_applied == Decimal("0.2500")
        assert payload.final_monthly_monotributo_fee == Decimal("712.50")

    def test_mides_ano_2_y_3(self):
        """Año 2 (50% = $1.425,00) y Año 3 (75% = $2.137,50)."""
        rules = get_monotributo_ruleset(2026)
        ui_val = get_ui_value(2026)
        assert rules is not None and ui_val is not None

        # Año 2 (Mes 18)
        profile_y2 = IndependentProfile(
            regime=IndependentTaxRegime.MONOTRIBUTO_MIDES,
            has_mides_certificate=True,
            mides_certificate_expiry=date(2027, 1, 1),
            regime_start_date=date(2025, 1, 1),
        )
        res_y2 = calculate_monotributo_settlement(
            annual_gross_sales_uyu=Decimal("300000.00"),
            profile=profile_y2,
            rules=rules,
            ui_value=ui_val,
            calculation_date=date(2026, 6, 1),
        )
        assert res_y2.monotributo_payload is not None
        assert res_y2.monotributo_payload.final_monthly_monotributo_fee == Decimal(
            "1425.00"
        )

        # Año 3 (Mes 30)
        profile_y3 = IndependentProfile(
            regime=IndependentTaxRegime.MONOTRIBUTO_MIDES,
            has_mides_certificate=True,
            mides_certificate_expiry=date(2027, 1, 1),
            regime_start_date=date(2024, 1, 1),
        )
        res_y3 = calculate_monotributo_settlement(
            annual_gross_sales_uyu=Decimal("300000.00"),
            profile=profile_y3,
            rules=rules,
            ui_value=ui_val,
            calculation_date=date(2026, 6, 1),
        )
        assert res_y3.monotributo_payload is not None
        assert res_y3.monotributo_payload.final_monthly_monotributo_fee == Decimal(
            "2137.50"
        )

    def test_mides_certificado_vencido_exige_revision_y_cuota_plena(self):
        """Certificado MIDES vencido liquida cuota plena (100%) y exige revisión."""
        rules = get_monotributo_ruleset(2026)
        ui_val = get_ui_value(2026)
        assert rules is not None and ui_val is not None

        profile = IndependentProfile(
            regime=IndependentTaxRegime.MONOTRIBUTO_MIDES,
            has_mides_certificate=True,
            mides_certificate_expiry=date(2025, 12, 31),  # Vencido al 2026
            regime_start_date=date(2026, 1, 1),
        )

        res = calculate_monotributo_settlement(
            annual_gross_sales_uyu=Decimal("300000.00"),
            profile=profile,
            rules=rules,
            ui_value=ui_val,
            calculation_date=date(2026, 6, 1),
        )

        assert res.status == CalculationStatus.REQUIRES_REVIEW
        assert res.monotributo_payload is not None
        assert res.monotributo_payload.is_mides_certificate_valid is False
        assert res.monotributo_payload.final_monthly_monotributo_fee == Decimal(
            "2850.00"
        )


class TestMonotributoOrchestration:
    """Verifica la orquestación a través del motor principal."""

    def test_engine_calculate_monotributo(self):
        """Prueba calculate_monotributo vía LaborCalculationEngine."""
        profile = IndependentProfile(
            regime=IndependentTaxRegime.MONOTRIBUTO,
            local_premises_sqm=Decimal("12.00"),
            employees_count=0,
            regime_start_date=date(2025, 1, 1),
        )

        result = LaborCalculationEngine.calculate_monotributo(
            annual_gross_sales_uyu=Decimal("600000.00"),
            profile=profile,
            fiscal_year=2026,
            calculation_date=date(2026, 6, 1),
        )

        assert result.status == CalculationStatus.CALCULATED
        assert result.monotributo_payload is not None
        assert result.total_withholdings == Decimal("2850.00")
