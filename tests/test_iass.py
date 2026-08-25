"""
Tests de invariantes para Pasividades, Jubilaciones y Pensiones — IASS (Fase 3D).
Valida MNI (9 BPC Ley 20.124), deducciones salud (14%/8%), FONASA y multicaixa.
"""

from __future__ import annotations

from decimal import Decimal

from services.labor.calculations.pension.iass_calculator import (
    calculate_pension_settlement,
)
from services.labor.domain.dtos import PensionProfile
from services.labor.domain.enums import (
    CalculationStatus,
    PensionFundType,
)
from services.labor.domain.tax_rules import (
    get_iass_ruleset,
    get_verified_bpc,
)
from services.labor.engine import LaborCalculationEngine


class TestIASSProgressiveScale:
    """Verifica el cálculo de IASS según escala progresiva (Ley 18.314 / Ley 20.124)."""

    def test_pasividad_bajo_9_bpc_exenta_de_iass(self):
        """Pasividad menor a 9 BPC ($63.324 en 2026) no paga IASS."""
        rules = get_iass_ruleset(2026)
        bpc = get_verified_bpc(2026)
        assert rules is not None and bpc is not None

        profile = PensionProfile(
            pension_fund=PensionFundType.BPS,
            monthly_pension_nominal=Decimal("50000.00"),
            has_fonasa_coverage=False,
        )

        res = calculate_pension_settlement(profile, rules, bpc)

        payload = res.iass_payload
        assert payload is not None
        assert payload.iass_gross_tax == Decimal("0.00")
        assert payload.iass_net_withholding == Decimal("0.00")
        assert payload.net_pension_liquid == Decimal("50000.00")

    def test_pasividad_tramo_2_entre_9_y_15_bpc(self):
        """Pasividad de $80.000 (~11.37 BPC) tributa 10% sobre el excedente de 9 BPC."""
        rules = get_iass_ruleset(2026)
        bpc = get_verified_bpc(2026)
        assert rules is not None and bpc is not None

        profile = PensionProfile(
            pension_fund=PensionFundType.BPS,
            monthly_pension_nominal=Decimal("80000.00"),
            has_fonasa_coverage=False,
        )

        res = calculate_pension_settlement(profile, rules, bpc)

        payload = res.iass_payload
        assert payload is not None
        # Excedente 9 BPC = 2.3701 BPC * 7036 * 10% = 1667.60
        assert payload.iass_gross_tax == Decimal("1667.60")

        # Deducción salud <= 15 BPC: 0.5 BPC ($3518) * 14% = 492.52
        assert payload.health_deduction_amount == Decimal("492.52")

        # IASS neto: 1667.60 - 492.52 = 1175.08
        assert payload.iass_net_withholding == Decimal("1175.08")
        assert payload.net_pension_liquid == Decimal("80000.00") - Decimal("1175.08")


class TestIASSMultiPensionConsolidation:
    """Verifica la consolidación de haberes de múltiples cajas previsionales."""

    def test_consolidacion_multicaixa_alcanza_tramo_superior(self):
        """Dos pasividades que aisladas no tributan, al consolidarse tributan IASS."""
        rules = get_iass_ruleset(2026)
        bpc = get_verified_bpc(2026)
        assert rules is not None and bpc is not None

        profile = PensionProfile(
            pension_fund=PensionFundType.BPS,
            monthly_pension_nominal=Decimal("60000.00"),
            secondary_pension_nominals=[Decimal("40000.00")],
            has_fonasa_coverage=False,
        )

        res = calculate_pension_settlement(profile, rules, bpc)

        payload = res.iass_payload
        assert payload is not None
        assert payload.is_multi_pension_consolidated is True
        assert payload.consolidated_gross_pension == Decimal("100000.00")

        # Excedente 9 BPC = 5.2129 BPC * 7036 * 10% = 3667.60
        assert payload.iass_gross_tax == Decimal("3667.59")

        # Retención proporcional al 60%: (3667.59 - 492.52) * 60% = 1905.04
        assert payload.iass_net_withholding == Decimal("1905.04")


class TestIASSPensionOrchestration:
    """Verifica la orquestación a través del motor principal."""

    def test_engine_calculate_pension_con_fonasa(self):
        """Prueba calculate_pension vía LaborCalculationEngine incluyendo FONASA."""
        profile = PensionProfile(
            pension_fund=PensionFundType.BPS,
            monthly_pension_nominal=Decimal("80000.00"),
            has_fonasa_coverage=True,
            fonasa_withholding_rate=Decimal("0.0450"),
        )

        result = LaborCalculationEngine.calculate_pension(
            profile=profile,
            fiscal_year=2026,
        )

        assert result.status == CalculationStatus.CALCULATED
        payload = result.iass_payload
        assert payload is not None

        # FONASA pasivo 4.5% de 80.000 = 3600.00
        assert payload.fonasa_pension_withholding == Decimal("3600.00")

        # Total retenciones = 1175.08 (IASS) + 3600.00 (FONASA) = 4775.08
        assert result.total_withholdings == Decimal("4775.08")
        assert result.liquid_amount == Decimal("80000.00") - Decimal("4775.08")
