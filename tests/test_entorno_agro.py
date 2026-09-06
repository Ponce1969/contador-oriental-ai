"""
Tests for Rural / Agro and Household hybrid mode (entorno).
"""

from datetime import date
from decimal import Decimal

import pytest
from result import Ok

from core.session import SessionManager, _sessions
from models.categories import ExpenseCategory, get_categories_for_entorno
from models.expense_model import Expense
from models.income_model import (
    Income,
    IncomeCategory,
    get_income_categories_for_entorno,
)
from repositories.expense_repository import ExpenseRepository
from repositories.income_repository import IncomeRepository
from services.domain.expense_service import ExpenseService
from services.domain.income_service import IncomeService


class TestEntornoCategories:
    """Test category filtering for household and rural environments."""

    def test_expense_categories_hogar(self):
        cats = get_categories_for_entorno("hogar")
        assert len(cats) > 0
        assert all(not c.name.startswith("AGRO_") for c in cats)
        assert ExpenseCategory.ALMACEN in cats
        assert ExpenseCategory.AGRO_COMBUSTIBLE not in cats

    def test_expense_categories_campo(self):
        cats = get_categories_for_entorno("campo")
        assert len(cats) > 0
        assert all(c.name.startswith("AGRO_") for c in cats)
        assert ExpenseCategory.AGRO_COMBUSTIBLE in cats
        assert ExpenseCategory.AGRO_VETERINARIA in cats
        assert ExpenseCategory.ALMACEN not in cats

    def test_expense_categories_consolidado(self):
        cats = get_categories_for_entorno("consolidado")
        assert len(cats) == len(list(ExpenseCategory))

    def test_income_categories_hogar(self):
        cats = get_income_categories_for_entorno("hogar")
        assert IncomeCategory.SUELDO in cats
        assert IncomeCategory.VENTA_GANADO not in cats

    def test_income_categories_campo(self):
        cats = get_income_categories_for_entorno("campo")
        assert IncomeCategory.VENTA_GANADO in cats
        assert IncomeCategory.VENTA_GRANOS in cats
        assert IncomeCategory.SUELDO not in cats

    def test_income_categories_consolidado(self):
        cats = get_income_categories_for_entorno(None)
        assert len(cats) == len(list(IncomeCategory))


class MockPage:
    class MockSession:
        id = "test-entorno-session-1"

    session = MockSession()


class TestSessionEntorno:
    """Test session manager helpers for campo enabled and active entorno."""

    @pytest.fixture(autouse=True)
    def clean_sessions(self):
        _sessions.clear()
        yield
        _sessions.clear()

    def test_session_campo_enabled_toggle(self):
        page = MockPage()

        assert not SessionManager.is_campo_enabled(page)

        SessionManager.set_campo_enabled(page, True)
        assert SessionManager.is_campo_enabled(page)

        SessionManager.set_campo_enabled(page, False)
        assert not SessionManager.is_campo_enabled(page)

    def test_session_active_entorno(self):
        page = MockPage()

        # Default is hogar
        assert SessionManager.get_active_entorno(page) == "hogar"

        SessionManager.set_active_entorno(page, "campo")
        assert SessionManager.get_active_entorno(page) == "campo"

        SessionManager.set_active_entorno(page, "hogar")
        assert SessionManager.get_active_entorno(page) == "hogar"


class TestExpenseAndIncomeEntornoServices:
    """Test filtering by entorno in ExpenseService and IncomeService."""

    @pytest.fixture
    def expense_service(self, db_session):
        repo = ExpenseRepository(db_session, familia_id=1)
        return ExpenseService(repo)

    @pytest.fixture
    def income_service(self, db_session):
        repo = IncomeRepository(db_session, familia_id=1)
        return IncomeService(repo)

    def test_expense_service_entorno_partitioning(self, expense_service):
        today = date.today()
        year = today.year
        month = today.month

        # Crear gasto de hogar
        exp_hogar = Expense(
            monto=Decimal("1500.00"),
            fecha=today,
            descripcion="Súper devoto hogar",
            categoria=ExpenseCategory.ALMACEN,
            currency="UYU",
            entorno="hogar",
        )
        res1 = expense_service.create_expense(exp_hogar)
        assert isinstance(res1, Ok)

        # Crear gasto de campo en USD
        exp_campo = Expense(
            monto=Decimal("450.00"),
            fecha=today,
            descripcion="Gasoil tractor campo",
            categoria=ExpenseCategory.AGRO_COMBUSTIBLE,
            currency="USD",
            entorno="campo",
        )
        res2 = expense_service.create_expense(exp_campo)
        assert isinstance(res2, Ok)

        # Listar filtrado por hogar
        hogar_list = expense_service.list_by_month(year, month, entorno="hogar")
        assert any(e.descripcion == "Súper devoto hogar" for e in hogar_list)
        assert not any(e.descripcion == "Gasoil tractor campo" for e in hogar_list)

        # Listar filtrado por campo
        campo_list = expense_service.list_by_month(year, month, entorno="campo")
        assert any(e.descripcion == "Gasoil tractor campo" for e in campo_list)
        assert not any(e.descripcion == "Súper devoto hogar" for e in campo_list)

        # Totales por entorno
        tot_campo_usd = expense_service.get_total_by_month(
            year, month, currency="USD", entorno="campo"
        )
        assert tot_campo_usd.get("USD", Decimal("0")) >= Decimal("450.00")

        tot_hogar_usd = expense_service.get_total_by_month(
            year, month, currency="USD", entorno="hogar"
        )
        assert tot_hogar_usd.get("USD", Decimal("0")) == Decimal("0")

    def test_income_service_entorno_partitioning(
        self, income_service, family_member_id
    ):
        today = date.today()
        year = today.year
        month = today.month

        # Ingreso hogar
        inc_hogar = Income(
            family_member_id=family_member_id,
            monto=Decimal("60000.00"),
            fecha=today,
            descripcion="Sueldo oficina",
            categoria=IncomeCategory.SUELDO,
            currency="UYU",
            entorno="hogar",
        )
        res1 = income_service.create_income(inc_hogar)
        assert isinstance(res1, Ok)

        # Ingreso campo
        inc_campo = Income(
            family_member_id=family_member_id,
            monto=Decimal("5000.00"),
            fecha=today,
            descripcion="Venta de terneros feria",
            categoria=IncomeCategory.VENTA_GANADO,
            currency="USD",
            entorno="campo",
        )
        res2 = income_service.create_income(inc_campo)
        assert isinstance(res2, Ok)

        # Listar filtrado por hogar
        hogar_list = income_service.list_for_month(year, month, entorno="hogar")
        assert any(i.descripcion == "Sueldo oficina" for i in hogar_list)
        assert not any(i.descripcion == "Venta de terneros feria" for i in hogar_list)

        # Listar filtrado por campo
        campo_list = income_service.list_for_month(year, month, entorno="campo")
        assert any(i.descripcion == "Venta de terneros feria" for i in campo_list)
        assert not any(i.descripcion == "Sueldo oficina" for i in campo_list)

        # Totales por entorno
        tot_campo = income_service.get_total_by_month(
            year, month, currency="USD", entorno="campo"
        )
        assert tot_campo.get("USD", Decimal("0")) >= Decimal("5000.00")
