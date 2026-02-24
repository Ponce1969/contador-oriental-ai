"""
Integration tests for complete user flows.
"""

from datetime import date

from result import Ok

from models.categories import ExpenseCategory
from models.expense_model import Expense
from models.income_model import Income, IncomeCategory
from models.user_model import UserCreate


class TestIntegrationFlows:
    """Integration tests for complete application flows."""

    def test_complete_user_registration_flow(self, db_session):
        """Test complete user registration and login flow."""
        from repositories.user_repository import UserRepository
        from services.auth_service import AuthService

        # Setup
        user_repo = UserRepository(session=db_session)
        auth_service = AuthService(user_repo)

        # Register user
        user_data = UserCreate(
            familia_id=1,
            username="integrationuser",
            password="password123",
            nombre_completo="Integration User",
        )
        result = auth_service.create_user(user_data)
        assert isinstance(result, Ok)

    def test_expense_tracking_flow(self, db_session):
        """Test complete expense tracking flow."""
        from repositories.expense_repository import ExpenseRepository
        from services.expense_service import ExpenseService

        # Setup
        repo = ExpenseRepository(db_session, familia_id=1)
        service = ExpenseService(repo)

        # Add expenses
        expenses = [
            Expense(
                monto=100.00,
                fecha=date.today(),
                descripcion="Grocery shopping",
                categoria=ExpenseCategory.ALMACEN,
            ),
            Expense(
                monto=50.00,
                fecha=date.today(),
                descripcion="Bus ticket",
                categoria=ExpenseCategory.VEHICULOS,
            ),
            Expense(
                monto=200.00,
                fecha=date.today(),
                descripcion="Electric bill",
                categoria=ExpenseCategory.HOGAR,
            ),
        ]

        for expense in expenses:
            result = service.create_expense(expense)
            assert isinstance(result, Ok)

        # Get summary
        summary = service.get_summary_by_categories()
        assert isinstance(summary, dict)
        assert len(summary) > 0

        # Verify total
        total = service.get_total_by_month(date.today().year, date.today().month)
        assert total >= 350.00

    def test_income_tracking_flow(self, db_session):
        """Test complete income tracking flow."""
        from repositories.income_repository import IncomeRepository
        from services.income_service import IncomeService

        # Setup
        repo = IncomeRepository(db_session, familia_id=1)
        service = IncomeService(repo)

        # Add incomes
        incomes = [
            Income(
                family_member_id=1,
                monto=2500.00,
                fecha=date.today(),
                descripcion="Salary",
                categoria=IncomeCategory.SUELDO,
            ),
            Income(
                family_member_id=1,
                monto=500.00,
                fecha=date.today(),
                descripcion="Freelance work",
                categoria=IncomeCategory.FREELANCE,
            ),
        ]

        for income in incomes:
            result = service.create_income(income)
            assert isinstance(result, Ok)

        # Get summary
        summary = service.get_summary_by_categories()
        assert isinstance(summary, dict)

        # Verify total
        total = service.get_total_by_month(date.today().year, date.today().month)
        assert total >= 3000.00

    def test_budget_balance_calculation(self, db_session):
        """Test budget balance calculation (income - expenses)."""
        from repositories.expense_repository import ExpenseRepository
        from repositories.income_repository import IncomeRepository
        from services.expense_service import ExpenseService
        from services.income_service import IncomeService

        # Setup services
        expense_repo = ExpenseRepository(db_session, familia_id=1)
        income_repo = IncomeRepository(db_session, familia_id=1)
        expense_service = ExpenseService(expense_repo)
        income_service = IncomeService(income_repo)

        # Add income
        income = Income(
            family_member_id=1,
            monto=3000.00,
            fecha=date.today(),
            descripcion="Monthly salary",
            categoria=IncomeCategory.SUELDO,
        )
        income_service.create_income(income)

        # Add expenses
        expenses = [
            Expense(
                monto=800.00,
                fecha=date.today(),
                descripcion="Rent",
                categoria=ExpenseCategory.HOGAR,
            ),
            Expense(
                monto=400.00,
                fecha=date.today(),
                descripcion="Groceries",
                categoria=ExpenseCategory.ALMACEN,
            ),
            Expense(
                monto=200.00,
                fecha=date.today(),
                descripcion="Utilities",
                categoria=ExpenseCategory.HOGAR,
            ),
        ]

        for expense in expenses:
            expense_service.create_expense(expense)

        # Calculate balance
        total_income = income_service.get_total_by_month(
            date.today().year, date.today().month
        )
        total_expenses = expense_service.get_total_by_month(
            date.today().year, date.today().month
        )
        balance = total_income - total_expenses

        assert total_income >= 3000.00
        assert total_expenses >= 1400.00
        assert balance > 0  # Should have positive balance
