"""
Tests unitarios y de integración para LaborController y simulaciones UI (Fase 3).
Verifica:
- Conversión estricta str -> Decimal (cero float)
- Cero efectos secundarios en DB durante simulación (aislamiento)
- Propagación de status, reglas legales y auditoría
- Separación de pipelines por régimen
- Ausencia de fórmulas fiscales en el Controller
"""

from __future__ import annotations

from decimal import Decimal

from controllers.labor_controller import LaborController, parse_decimal
from core.sqlalchemy_session import get_db_session
from database.tables import EconomicActivityTable
from services.labor.domain.dtos import IndependentProfile, PensionProfile
from services.labor.domain.enums import (
    CalculationStatus,
    EligibilityStatus,
    FonasaBeneficiaryType,
    IndependentTaxRegime,
    PensionFundType,
)
from services.labor.domain.models import TaxProfile


def test_parse_decimal_valid_cases():
    """Valida conversiones válidas de str a Decimal con cero float."""
    cases = [
        ("80000.00", Decimal("80000.00")),
        ("80000,50", Decimal("80000.50")),
        ("1.250,75", Decimal("1250.75")),
        ("$ 45000", Decimal("45000")),
        ("  120000.00  ", Decimal("120000.00")),
        ("", Decimal("0.00")),
        (None, Decimal("0.00")),
    ]
    for raw_input, expected in cases:
        res = parse_decimal(raw_input)
        assert res.is_ok(), f"Falló conversión para: {raw_input}"
        val = res.unwrap()
        assert isinstance(val, Decimal)
        assert val == expected


def test_parse_decimal_invalid_cases():
    """
    Valida que strings no numéricos retornen Err sin excepciones no controladas.
    """
    invalid_cases = [
        "abc",
        "12.34.56",
        "NaN",
        "Infinity",
        "-inf",
        "1e5",
        "$$$",
    ]
    for invalid in invalid_cases:
        res = parse_decimal(invalid)
        assert res.is_err(), f"Debería haber fallado para: {invalid}"


def test_simulation_has_zero_db_side_effects():
    """
    Verifica que las llamadas a los métodos de simulación NO persistan datos
    en la base de datos (Invariante de Fase 3).
    """
    controller = LaborController(familia_id=1)

    with get_db_session() as session:
        initial_count = session.query(EconomicActivityTable).count()

    # 1. Simular dependiente
    res_dep = controller.simulate_dependent(
        nominal_str="95000.00",
        tax_profile=TaxProfile(children_count=2, has_spouse_charge=True),
    )
    assert res_dep.is_ok()

    # 2. Simular servicios personales
    res_ind = controller.simulate_personal_services(
        billed_str="120000.00",
        profile=IndependentProfile(
            regime=IndependentTaxRegime.SERVICIOS_PERSONALES,
            pension_fund=PensionFundType.CJPPU,
            cjppu_category=2,
        ),
    )
    assert res_ind.is_ok()

    # 3. Simular Literal E
    res_lite = controller.simulate_literal_e(
        annual_sales_str="900000.00",
        profile=IndependentProfile(regime=IndependentTaxRegime.LITERAL_E),
    )
    assert res_lite.is_ok()

    # 4. Simular Monotributo
    res_mono = controller.simulate_monotributo(
        annual_sales_str="500000.00",
        profile=IndependentProfile(regime=IndependentTaxRegime.MONOTRIBUTO),
    )
    assert res_mono.is_ok()

    # 5. Simular Pasividad
    res_pas = controller.simulate_pension(
        profile=PensionProfile(
            pension_fund=PensionFundType.BPS,
            monthly_pension_nominal=Decimal("60000.00"),
        )
    )
    assert res_pas.is_ok()

    # Verificar que el conteo en la base de datos sea IDÉNTICO
    with get_db_session() as session:
        final_count = session.query(EconomicActivityTable).count()
        assert final_count == initial_count, "La simulación modificó la base de datos!"


def test_simulate_dependent_pipeline_and_audit():
    """
    Verifica que el desglose de dependiente calcule retenciones y conserve trazabilidad.
    """
    controller = LaborController(familia_id=1)
    res = controller.simulate_dependent(
        nominal_str="100000.00",
        tax_profile=TaxProfile(
            children_count=1,
            fonasa_type=FonasaBeneficiaryType.WITH_CHILDREN_NO_SPOUSE,
        ),
    )
    assert res.is_ok()
    calc = res.unwrap()

    assert calc.status in (CalculationStatus.CALCULATED, CalculationStatus.PROVISIONAL)
    assert calc.nominal_amount == Decimal("100000.00")
    assert calc.montepio_amount == Decimal("15000.00")
    assert calc.frl_amount == Decimal("100.00")
    assert calc.fonasa_amount > Decimal("0.00")
    assert calc.liquid_amount < Decimal("100000.00")
    assert calc.liquid_amount > Decimal("50000.00")

    # Auditoría
    assert len(calc.rule_version) > 0
    assert len(calc.legal_references) > 0


def test_simulate_literal_e_exceeded_threshold_propagation():
    """
    Verifica que si la facturación supera 305.000 UI, se propague la inelegibilidad.
    """
    controller = LaborController(familia_id=1)
    # 3.000.000 UYU está muy por encima de 305.000 UI (~1.900.000 UYU)
    res = controller.simulate_literal_e(
        annual_sales_str="3000000.00",
        profile=IndependentProfile(regime=IndependentTaxRegime.LITERAL_E),
    )
    assert res.is_ok()
    calc = res.unwrap()
    assert calc.eligibility is not None
    assert calc.eligibility.status == EligibilityStatus.INELIGIBLE
    assert len(calc.eligibility.violations) > 0


def test_simulate_monotributo_social_mides_subsidy():
    """Verifica el cálculo de cuota para Monotributo Social MIDES."""
    controller = LaborController(familia_id=1)
    res = controller.simulate_monotributo(
        annual_sales_str="300000.00",
        profile=IndependentProfile(
            regime=IndependentTaxRegime.MONOTRIBUTO_MIDES,
            has_mides_certificate=True,
        ),
    )
    assert res.is_ok()
    calc = res.unwrap()
    assert calc.monotributo_payload is not None
    assert calc.monotributo_payload.is_mides_regime is True
    assert calc.monotributo_payload.final_monthly_monotributo_fee > Decimal("0.00")


def test_simulate_pension_iass_withholding():
    """Verifica la simulación de pasividades e IASS para jubilados."""
    controller = LaborController(familia_id=1)
    res = controller.simulate_pension(
        profile=PensionProfile(
            pension_fund=PensionFundType.BPS,
            monthly_pension_nominal=Decimal("120000.00"),
            has_fonasa_coverage=True,
        )
    )
    assert res.is_ok()
    calc = res.unwrap()
    assert calc.iass_payload is not None
    assert calc.iass_payload.gross_pension_amount == Decimal("120000.00")
    assert calc.iass_payload.iass_net_withholding > Decimal("0.00")
    assert calc.iass_payload.net_pension_liquid < Decimal("120000.00")
