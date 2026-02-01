"""
Tests for ExpenseService.
"""

from datetime import date

import pytest
from result import Err, Ok

from models.categories import ExpenseCategory, PaymentMethod, RecurrenceFrequency
from models.errors import ValidationError
from models.expense_model import Expense
from services.expense_service import ExpenseService


class TestExpenseService:
    """Test cases for ExpenseService."""

    @pytest.fixture
    def service(self, db_session):
        """Create expense service with test repository."""
        from repositories.expense_repository import ExpenseRepository
        repo = ExpenseRepository(db_session, familia_id=1)
        return ExpenseService(repo)

    def test_create_expense_success(self, service, sample_expense_data):
        """Test successful expense creation."""
        expense = Expense(**sample_expense_data)
        result = service.create_expense(expense)

        assert isinstance(result, Ok)
        assert result.ok_value.monto == 150.50
        assert result.ok_value.descripcion == "Compra en supermercado"

    def test_create_expense_validation_error(self, service):
        """Test expense creation with invalid data raises Pydantic error."""
        from pydantic import ValidationError as PydanticError

        # Pydantic validates monto > 0 on model creation
        with pytest.raises(PydanticError):
            Expense(
                monto=-50.00,
                fecha=date.today(),
                descripcion="Invalid",
                categoria=ExpenseCategory.ALMACEN,
            )

    def test_create_expense_empty_description(self, service):
        """Test expense creation with empty description fails Pydantic validation."""
        from pydantic import ValidationError as PydanticError

        # Empty string fails min_length=1
        with pytest.raises(PydanticError):
            Expense(
                monto=100.00,
                fecha=date.today(),
                descripcion="",  # Empty string
                categoria=ExpenseCategory.ALMACEN,
            )

    def test_create_recurrent_without_frequency(self, service):
        """Test that recurrent expense without frequency fails."""
        expense = Expense(
            monto=500.00,
            fecha=date.today(),
            descripcion="Alquiler",
            categoria=ExpenseCategory.HOGAR,
            es_recurrente=True,
            frecuencia_recurrencia=None,
        )

        result = service.create_expense(expense)
        assert isinstance(result, Err)
        assert isinstance(result.err_value, ValidationError)

    def test_list_expenses(self, service, sample_expense_data):
        """Test listing expenses."""
        expense = Expense(**sample_expense_data)
        service.create_expense(expense)

        expenses = service.list_expenses()
        assert len(expenses) >= 1
        assert any(e.descripcion == "Compra en supermercado" for e in expenses)

    def test_get_expense_by_id(self, service, sample_expense_data):
        """Test getting expense by id."""
        expense = Expense(**sample_expense_data)
        created = service.create_expense(expense)

        if created.is_ok():
            expense_id = created.ok_value.id
            result = service.get_expense(expense_id)
            assert isinstance(result, Ok)

    def test_delete_expense(self, service, sample_expense_data):
        """Test deleting expense."""
        expense = Expense(**sample_expense_data)
        created = service.create_expense(expense)

        if created.is_ok():
            expense_id = created.ok_value.id
            result = service.delete_expense(expense_id)
            assert isinstance(result, Ok)

    def test_get_total_by_month(self, service):
        """Test getting total by month."""
        expense1 = Expense(
            monto=100.00,
            fecha=date.today(),
            descripcion="Gasto 1",
            categoria=ExpenseCategory.ALMACEN,
        )
        expense2 = Expense(
            monto=200.00,
            fecha=date.today(),
            descripcion="Gasto 2",
            categoria=ExpenseCategory.VEHICULOS,
        )

        service.create_expense(expense1)
        service.create_expense(expense2)

        total = service.get_total_by_month(date.today().year, date.today().month)
        assert total >= 300.00

    def test_get_summary_by_categories(self, service):
        """Test getting summary by categories."""
        expense1 = Expense(
            monto=100.00,
            fecha=date.today(),
            descripcion="Comida",
            categoria=ExpenseCategory.ALMACEN,
        )
        expense2 = Expense(
            monto=50.00,
            fecha=date.today(),
            descripcion="Comida 2",
            categoria=ExpenseCategory.ALMACEN,
        )

        service.create_expense(expense1)
        service.create_expense(expense2)

        summary = service.get_summary_by_categories()
        assert isinstance(summary, dict)
