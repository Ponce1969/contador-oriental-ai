"""
Tests for income_mappers.
"""
from datetime import date

from database.tables import IncomeTable
from models.income_model import Income, IncomeCategory
from models.categories import RecurrenceFrequency
from repositories.income_mappers import income_to_domain, income_to_table


class TestIncomeMappers:
    """Test cases for income mappers."""

    def test_income_table_to_domain(self):
        """Test converting IncomeTable to domain model."""
        table_row = IncomeTable(
            id=1,
            familia_id=1,
            family_member_id=1,
            monto=2500.00,
            fecha=date.today(),
            descripcion="Sueldo",
            categoria="💼 Sueldo",
            es_recurrente=True,
            frecuencia="Mensual",
            notas="Nota",
        )
        income = income_to_domain(table_row)

        assert income.id == 1
        assert income.monto == 2500.00
        assert income.categoria == IncomeCategory.SUELDO
        assert income.es_recurrente is True

    def test_income_domain_to_table(self):
        """Test converting domain model to IncomeTable."""
        income = Income(
            family_member_id=1,
            monto=3000.00,
            fecha=date.today(),
            descripcion="Freelance",
            categoria=IncomeCategory.FREELANCE,
            es_recurrente=False,
            notas="Test note",
        )
        table_row = income_to_table(income)

        assert table_row.monto == 3000.00
        assert "Freelance" in table_row.categoria
        assert table_row.es_recurrente is False

    def test_income_to_table_with_frequency(self):
        """Test converting income with recurrence frequency."""
        income = Income(
            familia_id=1,
            family_member_id=1,
            monto=1500.00,
            fecha=date.today(),
            descripcion="Alquiler",
            categoria=IncomeCategory.ALQUILER,
            es_recurrente=True,
            frecuencia=RecurrenceFrequency.MENSUAL,
        )
        table_row = income_to_table(income)

        assert table_row.frecuencia == "Mensual"
        assert table_row.es_recurrente is True

    def test_income_all_categories(self):
        """Test mapper with all income categories."""
        for category in IncomeCategory:
            income = Income(
                familia_id=1,
                family_member_id=1,
                monto=100.00,
                fecha=date.today(),
                descripcion="Test",
                categoria=category,
            )
            table_row = income_to_table(income)
            assert table_row.categoria == category.value

            # Test round-trip
            domain = income_to_domain(table_row)
            assert domain.categoria == category
