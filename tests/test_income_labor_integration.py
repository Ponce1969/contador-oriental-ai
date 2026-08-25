"""
Tests de integración para la vinculación entre ingresos y
actividades económicas laborales.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from controllers.income_controller import IncomeController
from controllers.labor_controller import LaborController
from database.tables import (
    Base,
    DependentDetailsTable,
    EconomicActivityTable,
    FamiliaTable,
    FamilyMemberTable,
    IncomeTable,
)
from models.income_model import (
    Income,
    IncomeCategory,
    RecurrenceFrequency,
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
from services.labor.engine import LaborCalculationEngine


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


class TestIncomeLaborIntegration:
    """Verifica que los ingresos puedan crearse y asociarse con la actividad económica."""

    def test_create_income_linked_to_economic_activity(self, db_session):
        labor_ctrl = LaborController(session=db_session, familia_id=1)
        income_ctrl = IncomeController(session=db_session, familia_id=1)

        # Crear actividad laboral
        tax_profile = TaxProfile(
            children_count=0,
            has_spouse_charge=False,
            fonasa_type=FonasaBeneficiaryType.SINGLE_NO_CHILDREN,
        )
        dependent_details = DependentDetails(
            remuneration_type=RemunerationType.MENSUAL,
            weekly_hours=40,
            estimated_monthly_nominal=Decimal("100000.00"),
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
        saved_act = labor_ctrl.add_activity(activity).unwrap()

        # Calcular líquido
        withholdings = LaborCalculationEngine.calculate_withholdings(
            nominal=Decimal("100000.00"),
            profile=tax_profile,
        )
        liquid_amount = withholdings.liquid_amount
        assert liquid_amount > 0

        # Crear ingreso asociado
        income = Income(
            family_member_id=10,
            economic_activity_id=saved_act.id,
            concept="salary",
            monto=liquid_amount,
            currency="UYU",
            fecha=date.today(),
            descripcion="Cobro de sueldo mensual",
            categoria=IncomeCategory.SUELDO,
            es_recurrente=True,
            frecuencia=RecurrenceFrequency.MENSUAL,
        )

        res = income_ctrl.add_income(income)
        assert res.is_ok()
        saved_income = res.unwrap()
        assert saved_income.id is not None
        assert saved_income.economic_activity_id == saved_act.id
        assert saved_income.monto == liquid_amount
        assert saved_income.concept == "salary"

        # Listar y comprobar persistencia
        incomes = income_ctrl.list_by_member(10)
        assert len(incomes) == 1
        assert incomes[0].economic_activity_id == saved_act.id
