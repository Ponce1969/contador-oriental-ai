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

    def test_login_invalid_credentials_format(self, controller):
        """Test login with invalid credentials format."""
        # Empty username should trigger validation error
        result = controller.login(
            username="",
            password="password123",
        )
        assert result.is_err()
        assert "Datos inválidos" in result.err_value.message


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

    def test_list_by_category(self, controller):
        """Test listing expenses by category."""
        expense = Expense(
            familia_id=1,
            monto=300.00,
            fecha=date.today(),
            descripcion="Category test",
            categoria=ExpenseCategory.OCIO,
        )
        controller.add_expense(expense)

        expenses = controller.list_by_category(ExpenseCategory.OCIO.value)
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

    def test_delete_expense(self, controller):
        """Test deleting expense through controller."""
        expense = Expense(
            familia_id=1,
            monto=100.00,
            fecha=date.today(),
            descripcion="To delete",
            categoria=ExpenseCategory.OTROS,
        )
        created = controller.add_expense(expense)

        if created.is_ok():
            expense_id = created.ok_value.id
            result = controller.delete_expense(expense_id)
            assert isinstance(result, Ok)

    def test_get_title(self, controller):
        """Test getting controller title."""
        title = controller.get_title()
        assert title == "Gastos Familiares"


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

    def test_list_by_member(self, controller):
        """Test listing incomes by member."""
        income = Income(
            familia_id=1,
            family_member_id=1,
            monto=2000.00,
            fecha=date.today(),
            descripcion="Member income",
            categoria=IncomeCategory.SUELDO,
        )
        controller.add_income(income)

        incomes = controller.list_by_member(1)
        assert len(incomes) >= 1

    def test_get_summary_by_categories(self, controller):
        """Test getting income summary by categories."""
        income = Income(
            familia_id=1,
            family_member_id=1,
            monto=1800.00,
            fecha=date.today(),
            descripcion="Summary test",
            categoria=IncomeCategory.SUELDO,
        )
        controller.add_income(income)

        summary = controller.get_summary_by_categories()
        assert isinstance(summary, dict)

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

    def test_delete_income(self, controller):
        """Test deleting income through controller."""
        income = Income(
            familia_id=1,
            family_member_id=1,
            monto=500.00,
            fecha=date.today(),
            descripcion="To delete",
            categoria=IncomeCategory.FREELANCE,
        )
        created = controller.add_income(income)

        if created.is_ok():
            income_id = created.ok_value.id
            result = controller.delete_income(income_id)
            assert isinstance(result, Ok)

    def test_update_income(self, controller):
        """Test updating income through controller."""
        income = Income(
            familia_id=1,
            family_member_id=1,
            monto=1000.00,
            fecha=date.today(),
            descripcion="Original",
            categoria=IncomeCategory.SUELDO,
        )
        created = controller.add_income(income)

        if created.is_ok():
            updated_income = created.ok_value
            updated_income.descripcion = "Updated"
            result = controller.update_income(updated_income)
            assert isinstance(result, Ok)
            assert result.ok_value.descripcion == "Updated"

    def test_get_title(self, controller):
        """Test getting controller title."""
        title = controller.get_title()
        assert title == "Ingresos Familiares"

