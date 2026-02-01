"""
Tests for Expense model.
"""

from datetime import date, timedelta

import pytest

from models.categories import ExpenseCategory, PaymentMethod, RecurrenceFrequency
from models.expense_model import Expense


class TestExpenseModel:
    """Test cases for Expense model."""

    def test_expense_creation_basic(self):
        """Test basic expense creation."""
        expense = Expense(
            monto=100.50,
            fecha=date.today(),
            descripcion="Test expense",
            categoria=ExpenseCategory.ALMACEN,
        )

        assert expense.monto == 100.50
        assert expense.descripcion == "Test expense"
        assert expense.categoria == ExpenseCategory.ALMACEN

    def test_expense_creation_full(self, sample_expense_data):
        """Test expense creation with all fields."""
        expense = Expense(**sample_expense_data)

        assert expense.monto == 150.50
        assert expense.descripcion == "Compra en supermercado"
        assert expense.categoria == ExpenseCategory.ALMACEN
        assert expense.subcategoria == "Verduras"
        assert expense.metodo_pago == PaymentMethod.EFECTIVO
        assert expense.es_recurrente is False
        assert expense.notas == "Nota de prueba"

    def test_expense_str_representation(self):
        """Test string representation of expense."""
        expense = Expense(
            monto=100.00,
            fecha=date.today(),
            descripcion="Compra test",
            categoria=ExpenseCategory.ALMACEN,
        )

        str_repr = str(expense)
        assert "ALMACEN" in str_repr or "🛒" in str_repr
        assert "Compra test" in str_repr
        assert "100.00" in str_repr or "$100" in str_repr

    def test_expense_categoria_nombre(self):
        """Test categoria_nombre property."""
        expense = Expense(
            monto=100.00,
            fecha=date.today(),
            descripcion="Test",
            categoria=ExpenseCategory.ALMACEN,
        )

        nombre = expense.categoria_nombre
        assert nombre == "Almacén"

    def test_expense_categoria_nombre_all_categories(self):
        """Test categoria_nombre for all categories."""
        for category in ExpenseCategory:
            expense = Expense(
                monto=100.00,
                fecha=date.today(),
                descripcion="Test",
                categoria=category,
            )
            # Should return name without emoji
            assert len(expense.categoria_nombre) > 0
            assert expense.categoria_nombre in category.value

    def test_expense_recurrente(self):
        """Test recurrent expense creation."""
        expense = Expense(
            monto=500.00,
            fecha=date.today(),
            descripcion="Alquiler",
            categoria=ExpenseCategory.HOGAR,
            es_recurrente=True,
            frecuencia_recurrencia=RecurrenceFrequency.MENSUAL,
        )

        assert expense.es_recurrente is True
        assert expense.frecuencia_recurrencia == RecurrenceFrequency.MENSUAL

    def test_expense_validation_monto_positivo(self):
        """Test that expense amount must be positive."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Expense(
                monto=0,
                fecha=date.today(),
                descripcion="Test",
                categoria=ExpenseCategory.ALMACEN,
            )

    def test_expense_validation_descripcion_requerida(self):
        """Test that description is required."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Expense(
                monto=100.00,
                fecha=date.today(),
                descripcion="",
                categoria=ExpenseCategory.ALMACEN,
            )

    def test_expense_default_values(self):
        """Test default values for optional fields."""
        expense = Expense(
            monto=100.00,
            descripcion="Test",
            categoria=ExpenseCategory.ALMACEN,
        )

        assert expense.fecha == date.today()
        assert expense.es_recurrente is False
        assert expense.frecuencia_recurrencia is None
        assert expense.subcategoria is None
        assert expense.notas is None

    def test_expense_id_assignment(self):
        """Test that expense id can be assigned."""
        expense = Expense(
            id=123,
            monto=100.00,
            fecha=date.today(),
            descripcion="Test",
            categoria=ExpenseCategory.ALMACEN,
        )

        assert expense.id == 123
