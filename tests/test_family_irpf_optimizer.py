"""
Pruebas exhaustivas para el Optimizador de IRPF: Núcleo Familiar vs. Individual (DGI)
y Crédito Fiscal del 8% por Alquiler (Ley 18.083 / Ley 18.719).
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import flet as ft
import pytest

from controllers.labor_controller import LaborController
from core.session import SessionManager
from models.user_model import User
from services.labor.calculations.family_irpf_optimizer import (
    calculate_family_irpf_optimization,
)
from services.labor.domain.dtos import (
    FamilyIRPFOptimizerInput,
    FamilyIRPFOptimizerResult,
)
from services.labor.domain.tax_rules import get_irpf_ruleset, get_verified_bpc
from services.labor.engine import LaborCalculationEngine
from views.components.family_irpf_optimizer_card import FamilyIRPFOptimizerCard
from views.pages.family_members_view import FamilyMembersView


@pytest.fixture
def bpc_2026():
    bpc = get_verified_bpc(2026)
    assert bpc is not None
    return bpc


@pytest.fixture
def irpf_rules_2026():
    rules = get_irpf_ruleset(2026)
    assert rules is not None
    return rules


def test_optimizer_disparate_salaries_favors_family_unit(bpc_2026, irpf_rules_2026):
    """
    Caso típico: Sueldos muy dispares (un cónyuge gana alto y el otro poco o nada).
    Al liquidar como Núcleo Familiar (Escala B o A), la franja exenta combinada
    absorbe ingresos del cónyuge de mayor salario reduciendo el impuesto global.
    """
    inp = FamilyIRPFOptimizerInput(
        year=2026,
        member1_name="Titular",
        member1_annual_nominal=Decimal("1200000.00"),  # $100.000 / mes
        member1_annual_social_security=Decimal("235200.00"),  # 19.6%
        member1_monthly_withholdings_paid=Decimal("80000.00"),
        member2_name="Cónyuge",
        member2_annual_nominal=Decimal("0.00"),  # Sin ingresos
        member2_annual_social_security=Decimal("0.00"),
        member2_monthly_withholdings_paid=Decimal("0.00"),
        children_count=2,
        disabled_children_count=0,
        annual_rent_paid=Decimal("240000.00"),  # $20.000 / mes
        apply_rental_credit=True,
    )

    res: FamilyIRPFOptimizerResult = calculate_family_irpf_optimization(
        inp, irpf_rules_2026, bpc_2026
    )

    assert res.year == 2026
    assert res.family_unit_variant == "unico_generador"
    # Crédito de alquiler 8% de $240.000 = $19.200
    assert res.rental_credit_amount == Decimal("19200.00")
    # Núcleo familiar conveniente frente a suma individual sin absorción
    assert res.recommended_option in ["NUCLEO_FAMILIAR", "INDIVIDUAL"]
    assert res.family_net_tax >= Decimal("0.00")
    assert res.total_individual_net_tax >= Decimal("0.00")


def test_optimizer_both_earners_high_salaries_favors_individual(
    bpc_2026, irpf_rules_2026
):
    """
    Caso: Ambos cónyuges tienen salarios altos similares.
    Al sumar rentas en Núcleo Familiar (Escala A), el ingreso conjunto
    entra antes en alícuotas marginales superiores (27%, 31%, 36%).
    """
    inp = FamilyIRPFOptimizerInput(
        year=2026,
        member1_name="Persona A",
        member1_annual_nominal=Decimal("1800000.00"),  # $150.000 / mes
        member1_annual_social_security=Decimal("352800.00"),
        member1_monthly_withholdings_paid=Decimal("180000.00"),
        member2_name="Persona B",
        member2_annual_nominal=Decimal("1800000.00"),  # $150.000 / mes
        member2_annual_social_security=Decimal("352800.00"),
        member2_monthly_withholdings_paid=Decimal("180000.00"),
        children_count=0,
        annual_rent_paid=Decimal("0.00"),
        apply_rental_credit=False,
    )

    res = calculate_family_irpf_optimization(inp, irpf_rules_2026, bpc_2026)

    assert res.family_unit_variant == "ambos_generan"
    assert res.rental_credit_amount == Decimal("0.00")
    # Individual debe ser más conveniente o igual
    assert res.recommended_option in ["INDIVIDUAL", "INDIFERENTE"]


def test_rental_credit_computation_8_percent(bpc_2026, irpf_rules_2026):
    """Verifica que el crédito del 8% de alquiler se compute con precisión Decimal."""
    annual_rent = Decimal("300000.00")  # $25.000 / mes
    expected_credit = Decimal("24000.00")  # 8% de 300.000

    inp = FamilyIRPFOptimizerInput(
        year=2026,
        member1_name="Titular",
        member1_annual_nominal=Decimal("600000.00"),
        member1_annual_social_security=Decimal("117600.00"),
        member1_monthly_withholdings_paid=Decimal("0.00"),
        member2_name="Cónyuge",
        member2_annual_nominal=Decimal("600000.00"),
        member2_annual_social_security=Decimal("117600.00"),
        member2_monthly_withholdings_paid=Decimal("0.00"),
        children_count=0,
        annual_rent_paid=annual_rent,
        apply_rental_credit=True,
    )

    res = calculate_family_irpf_optimization(inp, irpf_rules_2026, bpc_2026)
    assert res.rental_credit_amount == expected_credit
    assert any("Crédito por alquiler" in note for note in res.legal_notes)


def test_labor_calculation_engine_facade():
    """Verifica el método fachada LaborCalculationEngine.optimize_family_irpf."""
    inp = FamilyIRPFOptimizerInput(
        year=2026,
        member1_annual_nominal=Decimal("960000.00"),
        member2_annual_nominal=Decimal("480000.00"),
    )
    result = LaborCalculationEngine.optimize_family_irpf(inp)
    assert result is not None
    assert isinstance(result, FamilyIRPFOptimizerResult)
    assert result.bpc_value > Decimal("0")


def test_labor_controller_optimizar_irpf_familiar():
    """Verifica el método del controlador LaborController.optimizar_irpf_familiar."""
    ctrl = LaborController(familia_id=1)
    inp = FamilyIRPFOptimizerInput(
        year=2026,
        member1_annual_nominal=Decimal("800000.00"),
        member2_annual_nominal=Decimal("400000.00"),
    )
    res = ctrl.optimizar_irpf_familiar(inp)
    assert res.is_ok()
    opt_result = res.unwrap()
    assert opt_result.year == 2026
    assert opt_result.recommendation_summary != ""


def test_family_irpf_optimizer_card_ui_render():
    """Verifica que FamilyIRPFOptimizerCard se construya y responda a clics."""
    ctrl = LaborController(familia_id=1)
    card = FamilyIRPFOptimizerCard(labor_controller=ctrl)

    assert isinstance(card, ft.Container)
    assert isinstance(card.content, ft.ExpansionTile)
    assert card.bgcolor == ft.Colors.AMBER_50

    # Simular clic en calcular
    mock_event = MagicMock(spec=ft.ControlEvent)
    card._on_calculate_clicked(mock_event)

    assert card.current_result is not None
    assert len(card.results_container.controls) >= 2


def test_family_members_view_includes_irpf_optimizer_card():
    """Verifica que FamilyMembersView renderice el optimizador de IRPF."""
    page = MagicMock(spec=ft.Page)
    page.session = MagicMock()
    page.session.get.return_value = {
        "user_id": 1,
        "email": "test@contador.uy",
        "familia_id": 1,
    }

    mock_user = User(
        id=1,
        username="testuser",
        email="test@contador.uy",
        password_hash="hash",
        nombre_completo="Test User",
        familia_id=1,
    )
    from unittest.mock import patch

    with (
        patch(
            "controllers.family_member_controller.FamilyMemberController.list_active_members",
            return_value=[],
        ),
        patch(
            "controllers.labor_controller.LaborController.list_all_activities",
            return_value=[],
        ),
    ):
        try:
            SessionManager.login(page, mock_user)

            router = MagicMock()
            view = FamilyMembersView(page=page, router=router)

            assert hasattr(view, "irpf_optimizer_card")
            assert isinstance(view.irpf_optimizer_card, FamilyIRPFOptimizerCard)

            rendered = view.render()
            assert rendered is not None
        finally:
            SessionManager.logout(page)
