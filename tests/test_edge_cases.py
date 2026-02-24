"""
Tests for edge cases and error handling.
"""
from datetime import date, timedelta

import pytest
from pydantic import ValidationError as PydanticError
from result import Err, Ok

from models.categories import ExpenseCategory
from models.expense_model import Expense
from models.income_model import Income, IncomeCategory
from models.user_model import UserCreate


class TestValidationEdgeCases:
    """Test edge cases for model validation."""

    def test_expense_zero_amount(self):
        """Test expense with zero amount fails validation."""
        with pytest.raises(PydanticError):
            Expense(
                familia_id=1,
                monto=0,
                fecha=date.today(),
                descripcion="Test",
                categoria=ExpenseCategory.ALMACEN,
            )

    def test_expense_negative_amount(self):
        """Test expense with negative amount fails validation."""
        with pytest.raises(PydanticError):
            Expense(
                familia_id=1,
                monto=-100.00,
                fecha=date.today(),
                descripcion="Test",
                categoria=ExpenseCategory.ALMACEN,
            )

    def test_expense_empty_description(self):
        """Test expense with empty description fails validation."""
        with pytest.raises(PydanticError):
            Expense(
                familia_id=1,
                monto=100.00,
                fecha=date.today(),
                descripcion="",
                categoria=ExpenseCategory.ALMACEN,
            )

    def test_expense_future_date(self):
        """Test expense with future date is allowed."""
        future_date = date.today() + timedelta(days=30)
        expense = Expense(
            familia_id=1,
            monto=100.00,
            fecha=future_date,
            descripcion="Future expense",
            categoria=ExpenseCategory.HOGAR,
        )
        assert expense.fecha == future_date

    def test_income_zero_amount(self):
        """Test income with zero amount fails validation."""
        with pytest.raises(PydanticError):
            Income(
                familia_id=1,
                family_member_id=1,
                monto=0,
                fecha=date.today(),
                descripcion="Test",
                categoria=IncomeCategory.SUELDO,
            )

    def test_user_short_password(self):
        """Test user creation with short password fails."""
        with pytest.raises(PydanticError):
            UserCreate(
                familia_id=1,
                username="testuser",
                password="123",  # Too short
                nombre_completo="Test User",
            )

    def test_user_invalid_username(self):
        """Test user creation with invalid username fails."""
        with pytest.raises(PydanticError):
            UserCreate(
                familia_id=1,
                username="",  # Empty username
                password="password123",
                nombre_completo="Test User",
            )


class TestRepositoryErrorHandling:
    """Test repository error handling."""

    def test_get_nonexistent_expense(self, db_session):
        """Test getting non-existent expense returns error."""
        from repositories.expense_repository import ExpenseRepository

        repo = ExpenseRepository(db_session, familia_id=1)
        result = repo.get_by_id(99999)  # Non-existent ID

        assert result.is_err()
        assert "no encontrado" in result.err_value.message.lower()

    def test_get_nonexistent_income(self, db_session):
        """Test getting non-existent income returns error."""
        from repositories.income_repository import IncomeRepository

        repo = IncomeRepository(db_session, familia_id=1)
        result = repo.get_by_id(99999)  # Non-existent ID

        assert result.is_err()
        assert "no encontrado" in result.err_value.message.lower()

    def test_get_nonexistent_family_member(self, db_session):
        """Test getting non-existent family member returns error."""
        from repositories.family_member_repository import FamilyMemberRepository

        repo = FamilyMemberRepository(db_session, familia_id=1)
        result = repo.get_by_id(99999)  # Non-existent ID

        assert result.is_err()
        assert "no encontrado" in result.err_value.message.lower()


class TestBusinessRules:
    """Test business validation rules."""

    def test_recurrent_expense_without_frequency(self, db_session):
        """Test that recurrent expense without frequency is handled."""
        from repositories.expense_repository import ExpenseRepository
        from services.expense_service import ExpenseService

        repo = ExpenseRepository(db_session, familia_id=1)
        service = ExpenseService(repo)

        expense = Expense(
            familia_id=1,
            monto=500.00,
            fecha=date.today(),
            descripcion="Alquiler",
            categoria=ExpenseCategory.HOGAR,
            es_recurrente=True,
            frecuencia_recurrencia=None,
        )

        result = service.create_expense(expense)
        # The service should handle this validation
        assert isinstance(result, Err)

    def test_recurrent_income_without_frequency(self, db_session):
        """Test that recurrent income without frequency is handled."""
        from repositories.income_repository import IncomeRepository
        from services.income_service import IncomeService

        repo = IncomeRepository(db_session, familia_id=1)
        service = IncomeService(repo)

        income = Income(
            familia_id=1,
            family_member_id=1,
            monto=2000.00,
            fecha=date.today(),
            descripcion="Sueldo",
            categoria=IncomeCategory.SUELDO,
            es_recurrente=True,
            frecuencia=None,
        )

        result = service.create_income(income)
        # The service should handle this validation
        assert isinstance(result, Err)

    def test_duplicate_username(self, db_session):
        """Test that creating duplicate username fails."""
        from repositories.user_repository import UserRepository
        from services.auth_service import AuthService

        repo = UserRepository(session=db_session)
        service = AuthService(repo)

        # Create first user
        user1 = UserCreate(
            familia_id=1,
            username="duplicatetest",
            password="password123",
            nombre_completo="First User",
        )
        result1 = service.create_user(user1)
        assert isinstance(result1, Ok)

        # Try to create second user with same username
        user2 = UserCreate(
            familia_id=1,
            username="duplicatetest",
            password="different456",
            nombre_completo="Second User",
        )
        result2 = service.create_user(user2)
        assert isinstance(result2, Err)
