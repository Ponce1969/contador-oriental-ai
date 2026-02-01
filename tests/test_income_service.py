"""
Tests for IncomeService.
"""

from datetime import date

import pytest
from result import Err, Ok

from models.errors import ValidationError
from models.income_model import Income, IncomeCategory, RecurrenceFrequency
from services.income_service import IncomeService


class TestIncomeService:
    """Test cases for IncomeService."""

    @pytest.fixture
    def service(self, db_session):
        """Create income service with test repository."""
        from repositories.income_repository import IncomeRepository
        repo = IncomeRepository(db_session, familia_id=1)
        return IncomeService(repo)

    def test_create_income_success(self, service, sample_income_data):
        """Test successful income creation."""
        income = Income(**sample_income_data)
        result = service.create_income(income)

        assert isinstance(result, Ok)
        assert result.ok_value.monto == 2500.00
        assert result.ok_value.descripcion == "Sueldo mensual"

    def test_create_income_validation_error(self, service):
        """Test income creation with invalid data."""
        from pydantic import ValidationError as PydanticError

        with pytest.raises(PydanticError):
            Income(
                family_member_id=1,
                monto=0,
                fecha=date.today(),
                descripcion="Invalid",
                categoria=IncomeCategory.SUELDO,
            )

    def test_list_incomes(self, service, sample_income_data):
        """Test listing incomes."""
        income = Income(**sample_income_data)
        service.create_income(income)

        incomes = service.list_incomes()
        assert len(incomes) >= 1
        assert any(i.descripcion == "Sueldo mensual" for i in incomes)

    def test_get_income_by_id(self, service, sample_income_data):
        """Test getting income by id."""
        income = Income(**sample_income_data)
        created = service.create_income(income)

        if created.is_ok():
            income_id = created.ok_value.id
            result = service.get_income(income_id)
            assert isinstance(result, Ok)

    def test_delete_income(self, service, sample_income_data):
        """Test deleting income."""
        income = Income(**sample_income_data)
        created = service.create_income(income)

        if created.is_ok():
            income_id = created.ok_value.id
            result = service.delete_income(income_id)
            assert isinstance(result, Ok)

    def test_get_total_by_month(self, service):
        """Test getting total by month."""
        income1 = Income(
            family_member_id=1,
            monto=2500.00,
            fecha=date.today(),
            descripcion="Sueldo 1",
            categoria=IncomeCategory.SUELDO,
        )
        income2 = Income(
            family_member_id=1,
            monto=500.00,
            fecha=date.today(),
            descripcion="Extra",
            categoria=IncomeCategory.EXTRA,
        )

        service.create_income(income1)
        service.create_income(income2)

        total = service.get_total_by_month(date.today().year, date.today().month)
        assert total >= 3000.00

    def test_get_summary_by_categories(self, service):
        """Test getting summary by categories."""
        income1 = Income(
            family_member_id=1,
            monto=2500.00,
            fecha=date.today(),
            descripcion="Sueldo",
            categoria=IncomeCategory.SUELDO,
        )
        income2 = Income(
            family_member_id=1,
            monto=3000.00,
            fecha=date.today(),
            descripcion="Sueldo 2",
            categoria=IncomeCategory.SUELDO,
        )

        service.create_income(income1)
        service.create_income(income2)

        summary = service.get_summary_by_categories()
        assert isinstance(summary, dict)
