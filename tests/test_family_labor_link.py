"""
Tests de integración para el vínculo entre integrantes familiares
y actividades económicas.
"""

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from controllers.labor_controller import LaborController
from database.tables import (
    Base,
    DependentDetailsTable,
    EconomicActivityTable,
    FamiliaTable,
    FamilyMemberTable,
    IncomeTable,
    IndependentDetailsTable,
)
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


@pytest.fixture
def db_session():
    """Sesión de base de datos en memoria para pruebas."""
    engine = create_engine("sqlite:///:memory:")

    from typing import Any, cast

    Base.metadata.create_all(
        engine,
        tables=cast(
            Any,
            [
                FamiliaTable.__table__,
                FamilyMemberTable.__table__,
                EconomicActivityTable.__table__,
                DependentDetailsTable.__table__,
                IndependentDetailsTable.__table__,
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
        nombre="Micaela",
        tipo_miembro="persona",
        parentesco="madre",
        edad=65,
        estado_laboral="empleado",
        activo=True,
    )
    session.add(m1)
    session.commit()

    yield session
    session.close()


class TestFamilyLaborLink:
    """Verifica el flujo completo de vinculación entre miembro y actividad."""

    def test_add_and_list_economic_activity_for_member(self, db_session):
        controller = LaborController(session=db_session, familia_id=1)

        tax_profile = TaxProfile(
            children_count=1,
            has_spouse_charge=True,
            fonasa_type=FonasaBeneficiaryType.WITH_CHILDREN_AND_SPOUSE,
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

        add_res = controller.add_activity(activity)
        assert add_res.is_ok()
        saved = add_res.unwrap()
        assert saved.id is not None
        assert saved.family_member_id == 10
        assert saved.dependent_details is not None
        assert saved.dependent_details.estimated_monthly_nominal == Decimal("150000.00")

        # Listar actividades por miembro
        member_acts = controller.list_by_member(10)
        assert len(member_acts) == 1
        assert member_acts[0].family_member_id == 10
        assert member_acts[0].title == "Empleado Dependiente"

    def test_update_economic_activity_for_member(self, db_session):
        controller = LaborController(session=db_session, familia_id=1)

        # Crear actividad inicial
        activity = EconomicActivity(
            familia_id=1,
            family_member_id=10,
            nature=ActivityNature.DEPENDIENTE,
            title="Empleado Inicial",
            is_active=True,
            dependent_details=DependentDetails(
                estimated_monthly_nominal=Decimal("80000.00")
            ),
        )
        saved = controller.add_activity(activity).unwrap()

        # Actualizar sueldo nominal
        assert saved.dependent_details is not None
        saved.title = "Empleado Senior"
        saved.dependent_details.estimated_monthly_nominal = Decimal("160000.00")
        upd_res = controller.update_activity(saved)
        assert upd_res.is_ok()

        # Verificar persistencia
        acts = controller.list_by_member(10)
        assert len(acts) == 1
        assert acts[0].title == "Empleado Senior"
        assert acts[0].dependent_details is not None
        assert acts[0].dependent_details.estimated_monthly_nominal == Decimal(
            "160000.00"
        )
