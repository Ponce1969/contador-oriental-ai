"""
Tests de invariantes para el submotor de Servicios Personales (Fase 3A).
Valida elegibilidad, IVA (22%/10%), retenciones CEDE (60%), IRPF y CJPPU.
"""

from __future__ import annotations

from decimal import Decimal

from services.labor.calculations.independent.cjppu_calculator import (
    calculate_cjppu_contribution,
)
from services.labor.calculations.independent.eligibility import (
    PersonalServicesEligibilityEvaluator,
)
from services.labor.calculations.independent.irpf_independent import (
    calculate_bimonthly_irpf_advance,
)
from services.labor.calculations.independent.iva_calculator import (
    calculate_personal_services_vat,
)
from services.labor.domain.dtos import IndependentProfile
from services.labor.domain.enums import (
    CalculationStatus,
    EligibilityStatus,
    IndependentTaxRegime,
    PensionFundType,
)
from services.labor.domain.tax_rules import (
    get_cjppu_ruleset,
    get_irpf_independent_ruleset,
    get_iva_ruleset,
)
from services.labor.engine import LaborCalculationEngine


class TestPersonalServicesEligibility:
    """Valida la separación de elegibilidad fáctica antes del cálculo."""

    def test_perfil_incompleto_es_inelegible(self):
        """Sin declarar hechos esenciales, el perfil es inelegible."""
        profile = IndependentProfile(
            regime=IndependentTaxRegime.SERVICIOS_PERSONALES,
            is_professional=None,
            pension_fund=None,
        )
        res = PersonalServicesEligibilityEvaluator.evaluate(profile)

        assert res.status == EligibilityStatus.INELIGIBLE
        assert not res.can_proceed_to_calculation
        assert len(res.violations) >= 2

    def test_profesional_cjppu_sin_categoria_es_inelegible(self):
        """Profesional que declara CJPPU pero omite categoría (1-10) es inelegible."""
        profile = IndependentProfile(
            regime=IndependentTaxRegime.SERVICIOS_PERSONALES,
            is_professional=True,
            pension_fund=PensionFundType.CJPPU,
            cjppu_category=None,
        )
        res = PersonalServicesEligibilityEvaluator.evaluate(profile)

        assert res.status == EligibilityStatus.INELIGIBLE
        assert any("categoría" in v.lower() for v in res.violations)

    def test_profesional_valido_con_cjppu_es_elegible(self):
        """Profesional con todos los hechos declarados es elegible."""
        profile = IndependentProfile(
            regime=IndependentTaxRegime.SERVICIOS_PERSONALES,
            is_professional=True,
            pension_fund=PensionFundType.CJPPU,
            cjppu_category=2,
        )
        res = PersonalServicesEligibilityEvaluator.evaluate(profile)

        assert res.status == EligibilityStatus.ELIGIBLE
        assert res.can_proceed_to_calculation
        assert len(res.violations) == 0

    def test_gastos_reales_exigen_revision(self):
        """Optar por gastos reales permite calcular pero exige revisión documental."""
        profile = IndependentProfile(
            regime=IndependentTaxRegime.SERVICIOS_PERSONALES,
            is_professional=False,
            pension_fund=PensionFundType.BPS,
            opt_for_actual_expenses=True,
        )
        res = PersonalServicesEligibilityEvaluator.evaluate(profile)

        assert res.status == EligibilityStatus.REQUIRES_REVIEW
        assert res.can_proceed_to_calculation
        assert len(res.review_reasons) > 0


class TestPersonalServicesVAT:
    """Verifica el cálculo de IVA y retenciones CEDE."""

    def test_iva_tasa_basica_22_sin_retencion(self):
        """IVA 22% sobre facturación neta sin retención en origen."""
        rules = get_iva_ruleset(2026)
        assert rules is not None

        net_amount = Decimal("100000.00")
        res = calculate_personal_services_vat(
            net_amount, rules, rate_type="BASIC", is_client_cede=False
        )

        assert res.vat_rate_applied == Decimal("0.2200")
        assert res.vat_gross_amount == Decimal("22000.00")
        assert res.withholding_cede_amount == Decimal("0.00")
        assert res.vat_net_payable == Decimal("22000.00")

    def test_iva_tasa_minima_10_salud(self):
        """IVA 10% para servicios de salud humana."""
        rules = get_iva_ruleset(2026)
        assert rules is not None

        net_amount = Decimal("50000.00")
        res = calculate_personal_services_vat(
            net_amount, rules, rate_type="MINIMUM", is_client_cede=False
        )

        assert res.vat_rate_applied == Decimal("0.1000")
        assert res.vat_gross_amount == Decimal("5000.00")
        assert res.vat_net_payable == Decimal("5000.00")

    def test_iva_con_retencion_cede_60_porciento(self):
        """Cliente CEDE retiene el 60% del IVA devengado (Dec. 94/002)."""
        rules = get_iva_ruleset(2026)
        assert rules is not None

        net_amount = Decimal("100000.00")
        res = calculate_personal_services_vat(
            net_amount, rules, rate_type="BASIC", is_client_cede=True
        )

        assert res.vat_gross_amount == Decimal("22000.00")
        # 60% de 22.000 = 13.200
        assert res.withholding_cede_amount == Decimal("13200.00")
        # Neto a pagar DGI = 22.000 - 13.200 = 8.800
        assert res.vat_net_payable == Decimal("8800.00")


class TestPersonalServicesIRPF:
    """Verifica anticipos bimestrales con deducción ficta (30%) o real."""

    def test_anticipo_irpf_con_ficto_30(self):
        """Deducción ficta del 30%: base gravada 70%, anticipo 10%."""
        rules = get_irpf_independent_ruleset(2026)
        assert rules is not None

        billed_net = Decimal("200000.00")
        res = calculate_bimonthly_irpf_advance(
            billed_net, rules, withholdings_suffered=Decimal("0.00")
        )

        assert res.expense_deduction_amount == Decimal("60000.00")  # 30%
        assert res.taxable_base == Decimal("140000.00")  # 70%
        assert res.gross_advance_amount == Decimal("14000.00")  # 10%
        assert res.net_advance_payable == Decimal("14000.00")

    def test_anticipo_irpf_con_retenciones_sufridas(self):
        """Retenciones sufridas en el bimestre descuentan del anticipo a pagar."""
        rules = get_irpf_independent_ruleset(2026)
        assert rules is not None

        billed_net = Decimal("200000.00")
        withholdings = Decimal("9000.00")
        res = calculate_bimonthly_irpf_advance(
            billed_net, rules, withholdings_suffered=withholdings
        )

        assert res.gross_advance_amount == Decimal("14000.00")
        assert res.net_advance_payable == Decimal("5000.00")


class TestPersonalServicesCJPPU:
    """Verifica aportes a Caja Profesional según categorías trienales."""

    def test_aporte_cjppu_categoria_1_y_2(self):
        """Aporte 16.5% sobre sueldo ficto de la categoría."""
        rules = get_cjppu_ruleset(2026)
        assert rules is not None

        # Cat 1: $34.789 * 16.5% = $5.740,19 (ROUND_HALF_UP: 5740.185 -> 5740.19)
        res_cat1 = calculate_cjppu_contribution(1, rules)
        assert res_cat1.fictitious_salary == Decimal("34789.00")
        assert res_cat1.monthly_contribution_amount == Decimal("5740.19")

        # Cat 2: $42.520 * 16.5% = $7.015,80
        res_cat2 = calculate_cjppu_contribution(2, rules)
        assert res_cat2.fictitious_salary == Decimal("42520.00")
        assert res_cat2.monthly_contribution_amount == Decimal("7015.80")


class TestPersonalServicesFullOrchestration:
    """Verifica la orquestación completa a través de LaborCalculationEngine."""

    def test_liquidacion_integral_profesional_con_cjppu(self):
        """Liquidación para profesional universitario con CJPPU y cliente CEDE."""
        profile = IndependentProfile(
            regime=IndependentTaxRegime.SERVICIOS_PERSONALES,
            is_professional=True,
            pension_fund=PensionFundType.CJPPU,
            cjppu_category=2,
        )

        net_billed = Decimal("100000.00")
        result = LaborCalculationEngine.calculate_personal_services(
            net_billed_amount=net_billed,
            profile=profile,
            fiscal_year=2026,
            is_client_cede=True,
            vat_rate_type="BASIC",
            irpf_withholdings_suffered=Decimal("4000.00"),
        )

        assert result.status == CalculationStatus.CALCULATED
        payload = result.personal_services_payload
        assert payload is not None

        # IVA: 22.000, Retención CEDE: 13.200, Neto DGI: 8.800
        assert payload.vat_tax_amount == Decimal("22000.00")
        assert payload.vat_withholdings_suffered == Decimal("13200.00")
        assert payload.vat_net_payable == Decimal("8800.00")

        # IRPF: Base 70.000, Anticipo bruto 7.000, Retenciones 4.000, Neto DGI 3.000
        assert payload.irpf_taxable_base == Decimal("70000.00")
        assert payload.irpf_advance_amount == Decimal("7000.00")
        assert payload.irpf_net_advance_payable == Decimal("3000.00")

        # CJPPU Cat 2: 7.015,80
        assert payload.cjppu_monthly_amount == Decimal("7015.80")

        # Total impuestos y aportes a pagar
        total_payable = (
            payload.vat_net_payable
            + payload.irpf_net_advance_payable
            + payload.cjppu_monthly_amount
        )
        assert result.total_withholdings == total_payable

    def test_perfil_inelegible_retorna_insufficient_data(self):
        """Si el perfil no es elegible, el engine retorna INSUFFICIENT_DATA."""
        incomplete_profile = IndependentProfile(
            regime=IndependentTaxRegime.SERVICIOS_PERSONALES,
            is_professional=None,
            pension_fund=None,
        )

        result = LaborCalculationEngine.calculate_personal_services(
            net_billed_amount=Decimal("50000.00"),
            profile=incomplete_profile,
            fiscal_year=2026,
        )

        assert result.status == CalculationStatus.INSUFFICIENT_DATA
        assert result.eligibility is not None
        assert not result.eligibility.can_proceed_to_calculation
