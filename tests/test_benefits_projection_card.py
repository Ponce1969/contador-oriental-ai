"""
Tests para el componente BenefitsProjectionCard de beneficios laborales uruguayos.
"""

from datetime import date
from decimal import Decimal
from typing import Any, cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from controllers.family_member_controller import FamilyMemberController
from controllers.labor_controller import LaborController
from database.tables import (
    Base,
    DependentDetailsTable,
    EconomicActivityTable,
    FamiliaTable,
    FamilyMemberTable,
    IncomeTable,
)
from models.income_model import Income, IncomeCategory, RecurrenceFrequency
from services.labor.domain.enums import (
    ActivityNature,
    FonasaBeneficiaryType,
    RemunerationType,
)
from services.labor.domain.models import (
    DependentDetails,
    EconomicActivity,
    TaxProfile,
)
from views.components.benefits_projection_card import BenefitsProjectionCard


@pytest.fixture
def db_session():
    """Sesión de base de datos en memoria para pruebas."""
    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(
        engine,
        tables=cast(
            Any,
            [
                FamiliaTable.__table__,
                FamilyMemberTable.__table__,
                EconomicActivityTable.__table__,
                DependentDetailsTable.__table__,
                IncomeTable.__table__,
            ],
        ),
    )

    Session = sessionmaker(bind=engine)
    session = Session()

    f1 = FamiliaTable(id=1, nombre="Familia Gomez")
    session.add(f1)
    session.commit()

    m1 = FamilyMemberTable(
        id=10,
        familia_id=1,
        nombre="Admin Python",
        tipo_miembro="persona",
        parentesco="padre",
        edad=45,
        estado_laboral="empleado",
        activo=True,
    )
    session.add(m1)
    session.commit()

    yield session
    session.close()


class TestBenefitsProjectionCard:
    """Verifica que BenefitsProjectionCard renderice correctamente con datos de aguinaldo y salario vacacional."""

    def test_benefits_card_with_no_dependent_activities(self, db_session):
        labor_ctrl = LaborController(session=db_session, familia_id=1)
        member_ctrl = FamilyMemberController(session=db_session, familia_id=1)

        card = BenefitsProjectionCard(
            labor_controller=labor_ctrl,
            member_controller=member_ctrl,
            reference_date=date(2026, 8, 25),
        )

        assert card is not None
        assert len(card.content_column.controls) >= 2

    def test_benefits_card_with_dependent_activity(self, db_session):
        labor_ctrl = LaborController(session=db_session, familia_id=1)
        member_ctrl = FamilyMemberController(session=db_session, familia_id=1)

        # Crear actividad laboral
        tax_profile = TaxProfile(
            children_count=0,
            has_spouse_charge=False,
            fonasa_type=FonasaBeneficiaryType.SINGLE_NO_CHILDREN,
        )
        dependent_details = DependentDetails(
            remuneration_type=RemunerationType.MENSUAL,
            weekly_hours=40,
            estimated_monthly_nominal=Decimal("150000.00"),
            tax_profile=tax_profile,
        )
        activity = EconomicActivity(
            familia_id=1,
            family_member_id=10,
            nature=ActivityNature.DEPENDIENTE,
            title="Empleado Dependiente",
            is_active=True,
            dependent_details=dependent_details,
        )
        labor_ctrl.add_activity(activity)

        card = BenefitsProjectionCard(
            labor_controller=labor_ctrl,
            member_controller=member_ctrl,
            reference_date=date(2026, 8, 25),
        )

        card.refresh()
        assert len(card.content_column.controls) >= 3
