"""
Tests unitarios e integración para el Calendario Fiscal Oficial (DGI / BPS / CJPPU).
Verifica:
1. Trazabilidad normativa y fuentes oficiales publicadas.
2. Separación estricta de estado de fecha vs. estado de importe.
3. Invariantes de tipado: 100% Decimal y datetime.date (cero float).
4. Tests de invariantes: FALLBACK nunca se marca como OFFICIAL_VERIFIED.
5. Integración con el motor laboral, controlador y componente Flet UI.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from controllers.labor_controller import LaborController
from core.session import SessionManager
from services.labor.calculations.fiscal_calendar_calculator import (
    FiscalCalendarCalculator,
)
from services.labor.domain.dtos import IndependentProfile
from services.labor.domain.enums import (
    ActivityNature,
    IndependentTaxRegime,
    PensionFundType,
)
from services.labor.domain.fiscal_calendar_dtos import (
    AmountStatus,
    DateVerificationStatus,
    FiscalCalendarRequest,
    FiscalEntity,
    FiscalObligationType,
)
from services.labor.domain.fiscal_calendar_rules import (
    get_official_calendar_ruleset,
)
from services.labor.domain.models import EconomicActivity
from views.components.fiscal_calendar_card import FiscalCalendarCard
from views.pages.family_members_view import FamilyMembersView


class TestOfficialCalendarRulesets:
    """Valida la integridad de los datasets versionados oficiales."""

    def test_official_ruleset_2026_exists_with_audit_metadata(self):
        ruleset = get_official_calendar_ruleset(2026)
        assert ruleset is not None
        assert ruleset.fiscal_year == 2026
        assert ruleset.ruleset_version == "UY-FISCAL-CALENDAR-2026.1"
        assert len(ruleset.entries) > 0

        for entry in ruleset.entries:
            assert entry.source_document.strip() != ""
            assert entry.source_reference.strip() != ""
            assert entry.source_url.startswith("https://")
            assert entry.verification_status == DateVerificationStatus.OFFICIAL_VERIFIED
            assert isinstance(entry.due_date, date)

    def test_non_existent_year_returns_none(self):
        ruleset = get_official_calendar_ruleset(2099)
        assert ruleset is None


class TestFiscalCalendarCalculator:
    """Valida el cálculo determinístico de vencimientos por organismo."""

    def test_dgi_literal_e_due_dates_by_digit_group(self):
        req_0 = FiscalCalendarRequest(year=2026, month=3, rut_last_digit=1)
        res_0 = FiscalCalendarCalculator.calculate_calendar(req_0)
        target_ob = FiscalObligationType.LITERAL_E_CUOTA_MENSUAL
        lit_e_0 = next(
            (o for o in res_0.obligations if o.obligation_type == target_ob),
            None,
        )
        assert lit_e_0 is not None
        assert lit_e_0.due_date == date(2026, 3, 23)
        assert lit_e_0.date_status == DateVerificationStatus.OFFICIAL_VERIFIED

        req_9 = FiscalCalendarRequest(year=2026, month=3, rut_last_digit=9)
        res_9 = FiscalCalendarCalculator.calculate_calendar(req_9)
        lit_e_9 = next(
            (o for o in res_9.obligations if o.obligation_type == target_ob),
            None,
        )
        assert lit_e_9 is not None
        assert lit_e_9.due_date == date(2026, 3, 26)

    def test_dgi_irpf_bimonthly_advance_dates(self):
        target_ob = FiscalObligationType.IRPF_ANTICIPO_BIMESTRAL
        req_mar = FiscalCalendarRequest(year=2026, month=3, rut_last_digit=4)
        res_mar = FiscalCalendarCalculator.calculate_calendar(req_mar)
        irpf_ob = next(
            (o for o in res_mar.obligations if o.obligation_type == target_ob),
            None,
        )
        assert irpf_ob is not None
        assert irpf_ob.due_date == date(2026, 3, 25)
        assert "Bimestre Enero - Febrero 2026" in irpf_ob.target_period_label

        req_feb = FiscalCalendarRequest(year=2026, month=2, rut_last_digit=4)
        res_feb = FiscalCalendarCalculator.calculate_calendar(req_feb)
        irpf_feb = next(
            (o for o in res_feb.obligations if o.obligation_type == target_ob),
            None,
        )
        assert irpf_feb is None

    def test_bps_domestic_service_applies_to_all_digits(self):
        target_ob = FiscalObligationType.BPS_SERVICIO_DOMESTICO
        req_d0 = FiscalCalendarRequest(year=2026, month=3, rut_last_digit=0)
        req_d9 = FiscalCalendarRequest(year=2026, month=3, rut_last_digit=9)

        res_d0 = FiscalCalendarCalculator.calculate_calendar(req_d0)
        res_d9 = FiscalCalendarCalculator.calculate_calendar(req_d9)

        ob_d0 = next(
            (o for o in res_d0.obligations if o.obligation_type == target_ob),
            None,
        )
        ob_d9 = next(
            (o for o in res_d9.obligations if o.obligation_type == target_ob),
            None,
        )

        assert ob_d0 is not None and ob_d9 is not None
        assert ob_d0.due_date == date(2026, 3, 27)
        assert ob_d9.due_date == date(2026, 3, 27)

    def test_cjppu_official_payment_dates(self):
        req = FiscalCalendarRequest(year=2026, month=5)
        res = FiscalCalendarCalculator.calculate_calendar(req)
        target_ob = FiscalObligationType.CJPPU_APORTE_MENSUAL
        cjppu_ob = next(
            (o for o in res.obligations if o.obligation_type == target_ob),
            None,
        )
        assert cjppu_ob is not None
        assert cjppu_ob.due_date == date(2026, 5, 26)
        assert cjppu_ob.entity == FiscalEntity.CJPPU


class TestSeparationOfDateAndAmount:
    """Valida la separación estricta entre estado de fecha y estado de importe."""

    def test_exact_legal_amount_for_literal_e(self):
        act = EconomicActivity(
            id=1,
            familia_id=1,
            family_member_id=1,
            title="Kiosco",
            nature=ActivityNature.INDEPENDIENTE,
            is_active=True,
            independent_profile=IndependentProfile(
                regime=IndependentTaxRegime.LITERAL_E,
                estimated_monthly_gross_sales=Decimal("25000.00"),
                regime_start_date=date(2026, 1, 1),
            ),
        )
        req = FiscalCalendarRequest(year=2026, month=4, rut_last_digit=2)
        res = FiscalCalendarCalculator.calculate_calendar(req, activities=[act])

        target_ob = FiscalObligationType.LITERAL_E_CUOTA_MENSUAL
        lit_e = next(
            (o for o in res.obligations if o.obligation_type == target_ob),
            None,
        )
        assert lit_e is not None
        assert lit_e.date_status == DateVerificationStatus.OFFICIAL_VERIFIED
        assert lit_e.amount_status == AmountStatus.EXACT_LEGAL
        assert lit_e.estimated_amount is not None
        assert lit_e.estimated_amount > Decimal("0.00")

    def test_calculated_estimate_for_independent_irpf(self):
        act = EconomicActivity(
            id=2,
            familia_id=1,
            family_member_id=1,
            title="Consultoría",
            nature=ActivityNature.INDEPENDIENTE,
            is_active=True,
            independent_profile=IndependentProfile(
                regime=IndependentTaxRegime.SERVICIOS_PERSONALES,
                is_professional=False,
                pension_fund=PensionFundType.BPS,
                estimated_monthly_gross_sales=Decimal("80000.00"),
            ),
        )
        req = FiscalCalendarRequest(year=2026, month=3, rut_last_digit=5)
        res = FiscalCalendarCalculator.calculate_calendar(req, activities=[act])

        target_ob = FiscalObligationType.IRPF_ANTICIPO_BIMESTRAL
        irpf = next(
            (o for o in res.obligations if o.obligation_type == target_ob),
            None,
        )
        assert irpf is not None
        assert irpf.date_status == DateVerificationStatus.OFFICIAL_VERIFIED
        assert irpf.amount_status == AmountStatus.CALCULATED_ESTIMATE
        assert irpf.estimated_amount is not None
        assert irpf.estimated_amount > Decimal("0.00")

    def test_invariant_fallback_never_marked_as_official_verified(self):
        req = FiscalCalendarRequest(year=2030, month=1)
        res = FiscalCalendarCalculator.calculate_calendar(req)
        assert res.official_ruleset_version == "FALLBACK-NO-RULESET"
        for ob in res.obligations:
            assert ob.date_status != DateVerificationStatus.OFFICIAL_VERIFIED


class TestZeroFloatAudit:
    """Garantiza la política de cero float en importes y sumatorias."""

    def test_no_floats_in_summary_or_obligations(self):
        act = EconomicActivity(
            id=1,
            familia_id=1,
            family_member_id=1,
            title="Comercio",
            nature=ActivityNature.INDEPENDIENTE,
            is_active=True,
            independent_profile=IndependentProfile(
                regime=IndependentTaxRegime.LITERAL_E,
                estimated_monthly_gross_sales=Decimal("50000.00"),
            ),
        )
        req = FiscalCalendarRequest(year=2026, month=3, rut_last_digit=0)
        res = FiscalCalendarCalculator.calculate_calendar(req, activities=[act])

        assert isinstance(res.total_estimated_amount_uyu, Decimal)
        assert isinstance(res.total_estimated_amount_usd, Decimal)
        assert not isinstance(res.total_estimated_amount_uyu, float)

        for ob in res.obligations:
            if ob.estimated_amount is not None:
                assert isinstance(ob.estimated_amount, Decimal)
                assert not isinstance(ob.estimated_amount, float)


class TestControllerAndUiIntegration:
    """Valida la fachada en LaborController y la reactividad en UI."""

    def test_labor_controller_obtener_calendario_fiscal(self):
        controller = LaborController(familia_id=1)
        controller.list_all_activities = MagicMock(return_value=[])  # type: ignore
        res = controller.obtener_calendario_fiscal(year=2026, month=3, last_digit=2)
        assert res.is_ok()
        summary = res.unwrap()
        assert summary.year == 2026
        assert summary.month == 3
        assert len(summary.obligations) > 0

    def test_fiscal_calendar_card_component_rendering(self):
        controller = LaborController(familia_id=1)
        controller.list_all_activities = MagicMock(return_value=[])  # type: ignore
        card = FiscalCalendarCard(
            labor_controller=controller,
            initial_year=2026,
            initial_month=3,
        )
        assert card.current_summary is not None
        assert len(card.cards_container.controls) > 0
        assert card.bgcolor is not None

        mock_event = MagicMock()
        mock_event.control.selected = {"DGI"}
        card._on_entity_filter_changed(mock_event)
        assert card.selected_entity_filter == "DGI"

    def test_family_members_view_includes_fiscal_calendar(self):
        page = MagicMock()
        SessionManager.is_logged_in = MagicMock(return_value=True)  # type: ignore
        SessionManager.get_familia_id = MagicMock(return_value=1)  # type: ignore
        router = MagicMock()
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
            view = FamilyMembersView(page=page, router=router)
            assert hasattr(view, "fiscal_calendar_card")
            assert view.fiscal_calendar_card is not None
