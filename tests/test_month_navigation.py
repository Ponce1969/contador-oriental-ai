"""
Tests para navegación temporal, DTOs de transacciones mensuales y snapshots.
"""

from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text

from controllers.expense_controller import ExpenseController
from controllers.family_member_controller import FamilyMemberController
from controllers.history_controller import HistoryController, MonthTransactionsDTO
from controllers.income_controller import IncomeController
from core.session import SessionManager, _sessions
from database.tables import ExchangeRateTable
from models.categories import ExpenseCategory, PaymentMethod
from models.expense_model import Expense
from models.family_member_model import FamilyMember
from models.income_model import Income, IncomeCategory
from models.user_model import User
from repositories.exchange_rate_repository import ExchangeRateRepository
from repositories.monthly_snapshot_repository import MonthlySnapshotRepository


class MockSession:
    def __init__(self, session_id: str = "test-session-nav"):
        self.id = session_id


class MockPage:
    def __init__(self, session_id: str = "test-session-nav"):
        self.session = MockSession(session_id)
        self.data: dict = {}
        self.overlay: list = []

    def update(self):
        pass


@pytest.fixture(autouse=True)
def clean_sessions():
    _sessions.clear()
    yield
    _sessions.clear()


@pytest.fixture
def nav_family(db_engine):
    fam_id = 9991
    insert_sql = (
        f"INSERT INTO familias (id, nombre, email, activo, campo_enabled) "
        f"VALUES ({fam_id}, 'Familia Nav Test', 'nav{fam_id}@test.com', TRUE, FALSE) "
        f"ON CONFLICT (id) DO NOTHING"
    )
    with db_engine.connect() as conn:
        conn.execute(text(f"DELETE FROM expenses WHERE familia_id = {fam_id}"))
        conn.execute(text(f"DELETE FROM incomes WHERE familia_id = {fam_id}"))
        conn.execute(
            text(f"DELETE FROM monthly_expense_snapshots WHERE familia_id = {fam_id}")
        )
        conn.execute(text(f"DELETE FROM family_members WHERE familia_id = {fam_id}"))
        conn.execute(text(f"DELETE FROM familias WHERE id = {fam_id}"))
        conn.execute(text(insert_sql))
        conn.commit()

    yield fam_id

    with db_engine.connect() as conn:
        conn.execute(text(f"DELETE FROM expenses WHERE familia_id = {fam_id}"))
        conn.execute(text(f"DELETE FROM incomes WHERE familia_id = {fam_id}"))
        conn.execute(
            text(f"DELETE FROM monthly_expense_snapshots WHERE familia_id = {fam_id}")
        )
        conn.execute(text(f"DELETE FROM family_members WHERE familia_id = {fam_id}"))
        conn.execute(text(f"DELETE FROM familias WHERE id = {fam_id}"))
        conn.commit()


def test_session_manager_audited_period():
    """Verifica guardar y recuperar el período auditado en sesión."""
    page = MockPage()
    user = User(
        id=1,
        username="navuser",
        email="test@example.com",
        nombre="Test",
        password_hash="hash",
        familia_id=9991,
    )
    SessionManager.login(page, user)

    today = date.today()
    assert SessionManager.get_audited_period(page) == (today.year, today.month)

    SessionManager.set_audited_period(page, 2026, 4)
    assert SessionManager.get_audited_period(page) == (2026, 4)

    SessionManager.set_audited_period(page, 2025, 12)
    assert SessionManager.get_audited_period(page) == (2025, 12)


def test_month_transactions_dto_immutability():
    """Verifica que MonthTransactionsDTO sea inmutable."""
    dto = MonthTransactionsDTO(
        year=2026,
        month=5,
        label="Mayo 2026",
        expenses=[],
        incomes=[],
        total_gastos={"UYU": Decimal("1500")},
        total_ingresos={"UYU": Decimal("3000")},
        balance={"UYU": Decimal("1500")},
    )

    assert dto.year == 2026
    assert dto.month == 5
    assert dto.label == "Mayo 2026"
    assert dto.balance["UYU"] == Decimal("1500")
    assert dto.gastos == []
    assert dto.ingresos == []

    # Inmutabilidad (frozen=True)
    with pytest.raises(FrozenInstanceError):
        dto.year = 2027  # type: ignore


def test_history_controller_get_month_transactions(nav_family):
    """Verifica HistoryController para un mes específico."""
    familia_id = nav_family

    member_ctrl = FamilyMemberController(familia_id=familia_id)
    res_mem = member_ctrl.add_member(
        FamilyMember(
            familia_id=familia_id,
            nombre="Juan Prueba",
            parentesco="padre",
            tipo_miembro="persona",
            es_administrador=True,
            activo=True,
        )
    )
    assert res_mem.is_ok()
    member = res_mem.unwrap()

    inc_ctrl = IncomeController(familia_id=familia_id)
    res_inc = inc_ctrl.add_income(
        Income(
            family_member_id=member.id,
            monto=Decimal("50000"),
            currency="UYU",
            fecha=date(2026, 3, 15),
            descripcion="Sueldo Marzo",
            categoria=IncomeCategory.SUELDO,
            es_recurrente=False,
            entorno="hogar",
        )
    )
    assert res_inc.is_ok()

    exp_ctrl = ExpenseController(familia_id=familia_id)
    res_exp = exp_ctrl.add_expense(
        Expense(
            monto=Decimal("12000"),
            currency="UYU",
            fecha=date(2026, 3, 20),
            descripcion="Supermercado Marzo",
            categoria=ExpenseCategory.ALMACEN,
            metodo_pago=PaymentMethod.TARJETA_DEBITO,
            es_recurrente=False,
            entorno="hogar",
        )
    )
    assert res_exp.is_ok()

    hist_ctrl = HistoryController(familia_id=familia_id)
    trans = hist_ctrl.get_month_transactions(2026, 3)

    assert trans.year == 2026
    assert trans.month == 3
    assert len(trans.gastos) == 1
    assert trans.gastos[0].descripcion == "Supermercado Marzo"
    assert len(trans.ingresos) == 1
    assert trans.ingresos[0].descripcion == "Sueldo Marzo"
    assert trans.total_gastos["UYU"] == Decimal("12000")
    assert trans.total_ingresos["UYU"] == Decimal("50000")
    assert trans.balance["UYU"] == Decimal("38000")


def test_expense_snapshot_resync_on_past_date(db_session, nav_family):
    """Verifica recálculo de snapshots en mutaciones de meses pasados."""
    familia_id = nav_family
    exp_ctrl = ExpenseController(familia_id=familia_id)

    past_date = date(2026, 1, 10)
    res = exp_ctrl.add_expense(
        Expense(
            monto=Decimal("4500"),
            currency="UYU",
            fecha=past_date,
            descripcion="Gasto enero",
            categoria=ExpenseCategory.HOGAR,
            metodo_pago=PaymentMethod.EFECTIVO,
            es_recurrente=False,
            entorno="hogar",
        )
    )
    assert res.is_ok()
    expense_creado = res.unwrap()

    snap_repo = MonthlySnapshotRepository(db_session, familia_id=familia_id)
    snapshots = snap_repo.obtener_comparativa_mensual(2026, 1)
    assert len(snapshots) > 0
    snap_hogar = next(
        (s for s in snapshots if s.categoria == ExpenseCategory.HOGAR.value), None
    )
    assert snap_hogar is not None
    assert snap_hogar.total_actual >= Decimal("4500")

    expense_creado.monto = Decimal("7000")
    res_upd = exp_ctrl.update_expense(expense_creado)
    assert res_upd.is_ok()

    db_session.expire_all()
    snapshots_upd = snap_repo.obtener_comparativa_mensual(2026, 1)
    snap_hogar_upd = next(
        (s for s in snapshots_upd if s.categoria == ExpenseCategory.HOGAR.value), None
    )
    assert snap_hogar_upd is not None
    assert snap_hogar_upd.total_actual >= Decimal("7000")


def test_exchange_rate_get_rate_for_date(db_session):
    """Verifica obtención de cotización histórica con fallback."""
    repo = ExchangeRateRepository(db_session)

    row = ExchangeRateTable(
        currency_pair="USD/UYU",
        date=date(2026, 1, 15),
        compra=Decimal("42.50"),
        venta=Decimal("44.00"),
    )
    db_session.add(row)
    db_session.commit()

    rate_exact = repo.get_rate_for_date(date(2026, 1, 15))
    assert rate_exact is not None
    assert rate_exact.compra == Decimal("42.50")

    rate_later = repo.get_rate_for_date(date(2026, 1, 20))
    assert rate_later is not None
    assert rate_later.compra == Decimal("42.50")
