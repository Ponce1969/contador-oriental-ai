"""
Tests de invariantes para el submotor de retenciones e impuestos uruguayos (Fase 2).
Valida Cargas Sociales (Montepío, FRL), FONASA, IRPF y Cálculo Inverso determinístico.
"""

from __future__ import annotations

from decimal import Decimal

from services.labor.calculations.fonasa import calculate_fonasa
from services.labor.calculations.irpf import (
    calculate_annual_irpf_settlement,
    calculate_monthly_irpf_withholding,
)
from services.labor.calculations.social_security import calculate_social_security
from services.labor.calculations.withholdings import (
    calculate_monthly_withholdings,
    estimate_nominal_from_liquid,
)
from services.labor.domain.enums import (
    CalculationStatus,
    EstimationAccuracy,
    FonasaBeneficiaryType,
)
from services.labor.domain.models import TaxProfile
from services.labor.domain.tax_rules import (
    get_irpf_ruleset,
    get_social_security_ruleset,
    get_verified_bpc,
)


class TestSocialSecurityInvariants:
    """Verifica reglas de Montepío y Fondo de Reconversión Laboral."""

    def test_montepio_y_frl_calculo_exacto(self):
        """15% de Montepío y 0.10% de FRL sobre salario nominal."""
        rules = get_social_security_ruleset(2026)
        assert rules is not None

        nominal = Decimal("50000.00")
        res = calculate_social_security(nominal, rules)

        assert res.montepio_amount == Decimal("7500.00")
        assert res.frl_amount == Decimal("50.00")
        assert res.total_amount == Decimal("7550.00")
        assert not res.exceeds_cap

    def test_salario_supera_tope_bps_exige_revision(self):
        """Salarios que superan el tope máximo BPS/AFAP deben exigir revisión."""
        rules = get_social_security_ruleset(2026)
        assert rules is not None

        nominal = Decimal("300000.00")  # Supera tope de $255.000
        res = calculate_social_security(nominal, rules)

        assert res.exceeds_cap is True
        assert len(res.notes) > 0


class TestFonasaInvariants:
    """Verifica la matriz de FONASA y el umbral exacto de 2.5 BPC."""

    def test_fonasa_frontera_exacta_2_5_bpc(self):
        """En exactamente 2.5 BPC aplica la tasa base (3.0% para soltero sin hijos)."""
        rules = get_social_security_ruleset(2026)
        bpc = get_verified_bpc(2026)
        assert rules is not None and bpc is not None

        # BPC 2026 = 7036.00 -> 2.5 BPC = 17590.00
        exact_threshold = Decimal("2.5") * bpc.value
        profile = TaxProfile(fonasa_type=FonasaBeneficiaryType.SINGLE_NO_CHILDREN)

        res = calculate_fonasa(exact_threshold, profile, rules, bpc)

        assert not res.is_above_threshold
        assert res.effective_rate == Decimal("0.0300")
        assert res.fonasa_amount == (exact_threshold * Decimal("0.0300")).quantize(
            Decimal("0.01")
        )

    def test_fonasa_apenas_por_encima_2_5_bpc(self):
        """Con 0.01 UYU por encima de 2.5 BPC la tasa escala a 4.5%."""
        rules = get_social_security_ruleset(2026)
        bpc = get_verified_bpc(2026)
        assert rules is not None and bpc is not None

        just_above = (Decimal("2.5") * bpc.value) + Decimal("0.01")
        profile = TaxProfile(fonasa_type=FonasaBeneficiaryType.SINGLE_NO_CHILDREN)

        res = calculate_fonasa(just_above, profile, rules, bpc)

        assert res.is_above_threshold is True
        assert res.effective_rate == Decimal("0.0450")

    def test_fonasa_con_hijos_y_conyuge(self):
        """Composición familiar completa: 7% (<= 2.5 BPC) y 8% (> 2.5 BPC)."""
        rules = get_social_security_ruleset(2026)
        bpc = get_verified_bpc(2026)
        assert rules is not None and bpc is not None

        profile = TaxProfile(
            children_count=2,
            has_spouse_charge=True,
            fonasa_type=FonasaBeneficiaryType.WITH_CHILDREN_AND_SPOUSE,
        )

        nominal_alto = Decimal("60000.00")
        res = calculate_fonasa(nominal_alto, profile, rules, bpc)

        assert res.effective_rate == Decimal("0.0800")
        assert res.fonasa_amount == Decimal("4800.00")


class TestIRPFInvariants:
    """Verifica tramos progresivos, deducciones del 14%/8% y liquidación anual."""

    def test_salario_bajo_exento_de_irpf(self):
        """Salario nominal bajo donde la base con ficto no supera 7 BPC (0% IRPF)."""
        rules = get_irpf_ruleset(2026)
        bpc = get_verified_bpc(2026)
        assert rules is not None and bpc is not None

        # 7 BPC * 7036 = 49252. Base ficto $35.000 = $37.100 (< 7 BPC)
        nominal = Decimal("35000.00")
        ss_contributions = Decimal("6860.00")
        profile = TaxProfile()

        res = calculate_monthly_irpf_withholding(
            nominal, ss_contributions, profile, rules, bpc
        )

        assert res.gross_tax == Decimal("0.00")
        assert res.net_withholding == Decimal("0.00")

    def test_deduccion_frontera_15_bpc(self):
        """Deducciones aplican tasa 14% si nominal <= 15 BPC, y 8% si supera 15 BPC."""
        rules = get_irpf_ruleset(2026)
        bpc = get_verified_bpc(2026)
        assert rules is not None and bpc is not None

        exact_15_bpc = Decimal("15.0") * bpc.value
        just_above_15_bpc = exact_15_bpc + Decimal("0.01")
        ss_contributions = Decimal("15000.00")
        profile = TaxProfile(children_count=1)

        res_low = calculate_monthly_irpf_withholding(
            exact_15_bpc, ss_contributions, profile, rules, bpc
        )
        assert res_low.deduction_rate == Decimal("0.1400")

        res_high = calculate_monthly_irpf_withholding(
            just_above_15_bpc, ss_contributions, profile, rules, bpc
        )
        assert res_high.deduction_rate == Decimal("0.0800")

    def test_liquidacion_anual_irpf_diferencia_de_retencion_mensual(self):
        """La liquidación anual computa ingresos anuales reales sin ficto."""
        rules = get_irpf_ruleset(2026)
        bpc = get_verified_bpc(2026)
        assert rules is not None and bpc is not None

        annual_gross = Decimal("960000.00")  # $80.000 * 12
        annual_ss = Decimal("187200.00")
        monthly_retention_total = Decimal("36000.00")
        profile = TaxProfile(children_count=1)

        res = calculate_annual_irpf_settlement(
            annual_nominal_gross=annual_gross,
            annual_social_security_contributions=annual_ss,
            total_monthly_withholdings_paid=monthly_retention_total,
            profile=profile,
            rules=rules,
            bpc=bpc,
        )

        assert res.annual_gross_income == annual_gross
        assert res.annual_gross_tax > Decimal("0.00")
        assert res.annual_net_tax >= Decimal("0.00")
        # El saldo fiscal es determinístico
        assert res.fiscal_balance == res.annual_net_tax - monthly_retention_total


class TestWithholdingsOrchestrationAndInverse:
    """Verifica la orquestación completa y la bisección del cálculo inverso."""

    def test_simulacion_recibo_mensual_completa(self):
        """Verifica que el líquido sea exactamente Nominal - Total Descuentos."""
        ss_rules = get_social_security_ruleset(2026)
        irpf_rules = get_irpf_ruleset(2026)
        bpc = get_verified_bpc(2026)

        profile = TaxProfile(
            children_count=1,
            fonasa_type=FonasaBeneficiaryType.WITH_CHILDREN_NO_SPOUSE,
        )
        nominal = Decimal("75000.00")

        res = calculate_monthly_withholdings(
            nominal, profile, ss_rules, irpf_rules, bpc
        )

        assert res.status == CalculationStatus.CALCULATED
        assert res.nominal_amount == nominal
        assert res.total_withholdings == (
            res.montepio_amount
            + res.frl_amount
            + res.fonasa_amount
            + res.irpf_net_withholding
        )
        assert res.liquid_amount == nominal - res.total_withholdings

    def test_calculo_inverso_determinismo_e_invariante(self):
        """Verifica direct(estimate_nominal(L)).liquid ≈ L dentro de 0.01."""
        ss_rules = get_social_security_ruleset(2026)
        irpf_rules = get_irpf_ruleset(2026)
        bpc = get_verified_bpc(2026)

        profile = TaxProfile(
            children_count=2,
            has_spouse_charge=False,
            fonasa_type=FonasaBeneficiaryType.WITH_CHILDREN_NO_SPOUSE,
        )

        target_liquid = Decimal("54200.00")

        inv_res = estimate_nominal_from_liquid(
            liquid=target_liquid,
            profile=profile,
            ss_rules=ss_rules,
            irpf_rules=irpf_rules,
            bpc=bpc,
            tolerance=Decimal("0.01"),
        )

        assert inv_res.status in {
            EstimationAccuracy.EXACT,
            EstimationAccuracy.WITHIN_TOLERANCE,
        }
        assert inv_res.difference <= Decimal("0.01")
        assert inv_res.iterations_used <= 50

        # Verificación directa independiente
        direct_check = calculate_monthly_withholdings(
            inv_res.estimated_nominal, profile, ss_rules, irpf_rules, bpc
        )
        assert abs(direct_check.liquid_amount - target_liquid) <= Decimal("0.01")

    def test_guardas_de_seguridad_sin_bpc_valida(self):
        """Si BPC no verificada para el año, motor retorna REQUIRES_REVIEW."""
        ss_rules = get_social_security_ruleset(2026)
        irpf_rules = get_irpf_ruleset(2026)
        bpc_invalida = None

        profile = TaxProfile()
        nominal = Decimal("60000.00")

        res = calculate_monthly_withholdings(
            nominal, profile, ss_rules, irpf_rules, bpc_invalida
        )

        assert res.status == CalculationStatus.REQUIRES_REVIEW
        assert "No existe una BPC oficial verificada" in res.review_reasons[0]
