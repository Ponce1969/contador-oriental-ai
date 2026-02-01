"""
Tests for Controllers.
"""
from datetime import date

import pytest
from result import Ok

from models.categories import ExpenseCategory
from models.expense_model import Expense
from models.income_model import Income, IncomeCategory


class TestAuthController:
    """Test cases for AuthController."""

    @pytest.fixture
    def controller(self, db_session):
        """Create auth controller with mock page."""
        from controllers.auth_controller import AuthController
        # Mock page object
        class MockPage:
            pass
        return AuthController(MockPage())

    def test_login_failure(self, controller):
        """Test failed login through controller."""
        result = controller.login(
            username="nonexistent",
            password="wrongpassword",
        )
        assert result.is_err()


class TestExpenseController:
    """Test cases for ExpenseController."""

    @pytest.fixture
    def controller(self, db_session):
        """Create expense controller with test session."""
        from controllers.expense_controller import ExpenseController
        return ExpenseController(db_session, familia_id=1)

    def test_add_expense(self, controller):
        """Test adding expense through controller."""
        expense = Expense(
            familia_id=1,
            monto=150.00,
            fecha=date.today(),
            descripcion="Test expense",
            categoria=ExpenseCategory.ALMACEN,
        )
        result = controller.add_expense(expense)
        assert isinstance(result, Ok)
        assert result.ok_value.monto == 150.00

    def test_list_expenses(self, controller):
        """Test listing expenses through controller."""
        # Create an expense first
        expense = Expense(
            familia_id=1,
            monto=200.00,
            fecha=date.today(),
            descripcion="Another expense",
            categoria=ExpenseCategory.HOGAR,
        )
        controller.add_expense(expense)

        # Get all
        expenses = controller.list_expenses()
        assert len(expenses) >= 1

    def test_get_summary_by_categories(self, controller):
        """Test getting summary by categories through controller."""
        expense = Expense(
            familia_id=1,
            monto=300.00,
            fecha=date.today(),
            descripcion="Monthly test",
            categoria=ExpenseCategory.OCIO,
        )
        controller.add_expense(expense)

        summary = controller.get_summary_by_categories()
        assert isinstance(summary, dict)

    def test_get_total_by_month(self, controller):
        """Test getting total by month through controller."""
        expense = Expense(
            familia_id=1,
            monto=500.00,
            fecha=date.today(),
            descripcion="Test total",
            categoria=ExpenseCategory.ALMACEN,
        )
        controller.add_expense(expense)

        total = controller.get_total_by_month(date.today().year, date.today().month)
        assert total >= 500.00


class TestIncomeController:
    """Test cases for IncomeController."""

    @pytest.fixture
    def controller(self, db_session):
        """Create income controller with test session."""
        from controllers.income_controller import IncomeController
        return IncomeController(db_session, familia_id=1)

    def test_add_income(self, controller):
        """Test adding income through controller."""
        income = Income(
            familia_id=1,
            family_member_id=1,
            monto=2500.00,
            fecha=date.today(),
            descripcion="Test income",
            categoria=IncomeCategory.SUELDO,
        )
        result = controller.add_income(income)
        assert isinstance(result, Ok)
        assert result.ok_value.monto == 2500.00

    def test_list_incomes(self, controller):
        """Test listing incomes through controller."""
        income = Income(
            familia_id=1,
            family_member_id=1,
            monto=1500.00,
            fecha=date.today(),
            descripcion="Another income",
            categoria=IncomeCategory.FREELANCE,
        )
        controller.add_income(income)

        incomes = controller.list_incomes()
        assert len(incomes) >= 1

    def test_get_total_by_month(self, controller):
        """Test getting monthly total through controller."""
        income = Income(
            familia_id=1,
            family_member_id=1,
            monto=3000.00,
            fecha=date.today(),
            descripcion="Monthly income test",
            categoria=IncomeCategory.SUELDO,
        )
        controller.add_income(income)

        total = controller.get_total_by_month(date.today().year, date.today().month)
        assert total >= 3000.00
