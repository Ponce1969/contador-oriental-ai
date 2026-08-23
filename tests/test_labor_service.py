"""
Tests para LaborService y LaborController con persistencia en SQLite en memoria.
Verifica aislamiento multi-tenant y orquestación con IncomeRepository.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.tables import (
    Base,
    DependentDetailsTable,
    EconomicActivityTable,
    FamiliaTable,
    FamilyMemberTable,
    IncomeTable,
)
from models.income_model import Income, IncomeCategory
from repositories.economic_activity_repository import EconomicActivityRepository
from repositories.income_repository import IncomeRepository
from services.domain.labor_service import LaborService
from services.labor.domain.enums import (
    ActivityNature,
    CalculationStatus,
    RemunerationType,
)
from services.labor.domain.models import DependentDetails, EconomicActivity


@pytest.fixture
def db_session():
    """Sesión de base de datos en memoria para pruebas."""
    engine = create_engine("sqlite:///:memory:")

    # Crear solo las tablas relevantes para aislar el test
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

    # Seed de familias y miembros
    f1 = FamiliaTable(id=1, nombre="Familia Gomez")
    f2 = FamiliaTable(id=2, nombre="Familia Rodriguez")
    session.add_all([f1, f2])
    session.flush()

    m1 = FamilyMemberTable(
        id=10, familia_id=1, nombre="Gonzalo", tipo_miembro="persona"
    )
    m2 = FamilyMemberTable(id=20, familia_id=2, nombre="Carlos", tipo_miembro="persona")
    session.add_all([m1, m2])
    session.flush()

    yield session
    session.close()


def test_create_and_get_economic_activity(db_session):
    activity_repo = EconomicActivityRepository(db_session, familia_id=1)
    income_repo = IncomeRepository(db_session, familia_id=1)
    service = LaborService(activity_repo, income_repo)

    activity = EconomicActivity(
        familia_id=1,
        family_member_id=10,
        nature=ActivityNature.DEPENDIENTE,
        title="Empleado de Comercio",
        start_date=date(2025, 1, 1),
        dependent_details=DependentDetails(
            remuneration_type=RemunerationType.MENSUAL,
            weekly_hours=44,
            estimated_monthly_nominal=Decimal("55000.00"),
        ),
    )

    created_res = service.create_activity(activity)
    assert created_res.is_ok()
    created = created_res.unwrap()
    assert created.id is not None
    assert created.title == "Empleado de Comercio"
    assert created.dependent_details is not None
    assert created.dependent_details.estimated_monthly_nominal == Decimal("55000.00")

    # Recuperar por ID
    assert created.id is not None
    get_res = service.get_activity(created.id)
    assert get_res.is_ok()
    retrieved = get_res.unwrap()
    assert retrieved.id == created.id
    assert retrieved.dependent_details is not None
    assert retrieved.dependent_details.weekly_hours == 44


def test_multitenancy_isolation(db_session):
    """Familia 2 no puede acceder a las actividades de Familia 1."""
    repo_f1 = EconomicActivityRepository(db_session, familia_id=1)
    repo_f2 = EconomicActivityRepository(db_session, familia_id=2)
    income_repo = IncomeRepository(db_session, familia_id=1)
    service_f1 = LaborService(repo_f1, income_repo)
    service_f2 = LaborService(repo_f2, income_repo)

    activity = EconomicActivity(
        familia_id=1,
        family_member_id=10,
        title="Trabajo Familia 1",
        start_date=date(2025, 1, 1),
    )
    created = service_f1.create_activity(activity).unwrap()

    # Familia 2 intenta obtener la actividad de Familia 1
    assert created.id is not None
    assert service_f2.get_activity(created.id).is_err()
    assert len(service_f2.list_all_activities()) == 0


def test_calculate_aguinaldo_service_orchestration(db_session):
    """El servicio coordina los ingresos del repositorio con el motor de aguinaldo."""
    activity_repo = EconomicActivityRepository(db_session, familia_id=1)
    income_repo = IncomeRepository(db_session, familia_id=1)
    service = LaborService(activity_repo, income_repo)

    activity = EconomicActivity(
        familia_id=1,
        family_member_id=10,
        title="Empleado Tienda",
        start_date=date(2024, 1, 1),
        dependent_details=DependentDetails(
            estimated_monthly_nominal=Decimal("50000.00"),
        ),
    )
    saved_act = service.create_activity(activity).unwrap()

    # Registrar 6 meses de sueldos para Aguinaldo Junio 2026 (Dic 2025 - Mayo 2026)
    dates_and_salaries = [
        (date(2025, 12, 5), Decimal("50000.00")),
        (date(2026, 1, 5), Decimal("50000.00")),
        (date(2026, 2, 5), Decimal("50000.00")),
        (date(2026, 3, 5), Decimal("50000.00")),
        (date(2026, 4, 5), Decimal("50000.00")),
        (date(2026, 5, 5), Decimal("50000.00")),
    ]

    for d, monto in dates_and_salaries:
        inc = Income(
            family_member_id=10,
            economic_activity_id=saved_act.id,
            concept="salary",
            monto=monto,
            fecha=d,
            descripcion="Sueldo mensual",
            categoria=IncomeCategory.SUELDO,
        )
        income_repo.add(inc)

    assert saved_act.id is not None
    res = service.calculate_member_aguinaldo(
        activity_id=saved_act.id,
        year=2026,
        semester=1,
        today=date(2026, 6, 1),
    )

    assert res.is_ok()
    calc = res.unwrap()
    assert calc.status == CalculationStatus.CALCULATED
    # 6 * 50.000 = 300.000 / 12 = 25.000
    assert calc.total_computable == Decimal("300000.00")
    assert calc.final_amount == Decimal("25000.00")
