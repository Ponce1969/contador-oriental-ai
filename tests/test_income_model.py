"""
Tests for Income model.
"""

from datetime import date

import pytest

from models.income_model import Income, IncomeCategory, RecurrenceFrequency


class TestIncomeModel:
    """Test cases for Income model."""

    def test_income_creation_basic(self):
        """Test basic income creation."""
        income = Income(
            family_member_id=1,
            monto=2500.00,
            fecha=date.today(),
            descripcion="Sueldo",
            categoria=IncomeCategory.SUELDO,
        )

        assert income.monto == 2500.00
        assert income.descripcion == "Sueldo"
        assert income.categoria == IncomeCategory.SUELDO
        assert income.family_member_id == 1

    def test_income_creation_full(self, sample_income_data):
        """Test income creation with all fields."""
        income = Income(**sample_income_data)

        assert income.monto == 2500.00
        assert income.descripcion == "Sueldo mensual"
        assert income.categoria == IncomeCategory.SUELDO
        assert income.es_recurrente is True
        assert income.notas == "Pago mensual"

    def test_income_str_representation(self):
        """Test string representation of income."""
        income = Income(
            family_member_id=1,
            monto=3000.00,
            fecha=date.today(),
            descripcion="Sueldo",
            categoria=IncomeCategory.SUELDO,
        )

        str_repr = str(income)
        assert "SUELDO" in str_repr or "💼" in str_repr
        assert "Sueldo" in str_repr

    def test_income_categoria_nombre(self):
        """Test categoria_nombre property."""
        income = Income(
            family_member_id=1,
            monto=1000.00,
            fecha=date.today(),
            descripcion="Test",
            categoria=IncomeCategory.SUELDO,
        )

        nombre = income.categoria_nombre
        assert nombre == "Sueldo"

    def test_income_recurrente(self):
        """Test recurrent income creation."""
        income = Income(
            family_member_id=1,
            monto=500.00,
            fecha=date.today(),
            descripcion="Alquiler recibido",
            categoria=IncomeCategory.ALQUILER,
            es_recurrente=True,
            frecuencia=RecurrenceFrequency.MENSUAL,
        )

        assert income.es_recurrente is True
        assert income.frecuencia == RecurrenceFrequency.MENSUAL

    def test_income_validation_monto_positivo(self):
        """Test that income amount must be positive."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Income(
                family_member_id=1,
                monto=-100,
                fecha=date.today(),
                descripcion="Test",
                categoria=IncomeCategory.SUELDO,
            )

    def test_income_default_values(self):
        """Test default values for optional fields."""
        income = Income(
            family_member_id=1,
            monto=1000.00,
            descripcion="Test",
            categoria=IncomeCategory.SUELDO,
        )

        assert income.fecha == date.today()
        assert income.es_recurrente is False
        assert income.frecuencia is None
        assert income.notas is None

    def test_income_categories(self):
        """Test all income categories."""
        categories = [
            IncomeCategory.SUELDO,
            IncomeCategory.JORNAL,
            IncomeCategory.EXTRA,
            IncomeCategory.BONO,
            IncomeCategory.FREELANCE,
            IncomeCategory.NEGOCIO,
            IncomeCategory.ALQUILER,
            IncomeCategory.INVERSION,
            IncomeCategory.OTRO,
        ]

        for category in categories:
            income = Income(
                family_member_id=1,
                monto=100.00,
                fecha=date.today(),
                descripcion="Test",
                categoria=category,
            )
            assert income.categoria == category
