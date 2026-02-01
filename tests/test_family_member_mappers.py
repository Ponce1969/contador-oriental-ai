"""
Tests for family_member_mappers.
"""
from datetime import date

from database.tables import FamilyMemberTable
from models.family_member_model import FamilyMember, IncomeType
from repositories.family_member_mappers import (
    family_member_to_domain,
    family_member_to_table,
)


class TestFamilyMemberMappers:
    """Test cases for family member mappers."""

    def test_table_to_domain(self):
        """Test converting table row to domain model."""
        table_row = FamilyMemberTable(
            id=1,
            nombre="Juan",
            tipo_ingreso="Sueldo fijo",
            sueldo_mensual=2500.00,
            activo=True,
            notas="Test notes",
        )
        member = family_member_to_domain(table_row)

        assert member.id == 1
        assert member.nombre == "Juan"
        assert member.tipo_ingreso == IncomeType.FIJO
        assert member.sueldo_mensual == 2500.00
        assert member.activo is True

    def test_domain_to_table(self):
        """Test converting domain model to table row."""
        member = FamilyMember(
            nombre="María",
            tipo_ingreso=IncomeType.MIXTO,
            sueldo_mensual=1800.00,
            activo=True,
            notas="Notas de prueba",
        )
        table_row = family_member_to_table(member)

        assert table_row.nombre == "María"
        assert table_row.tipo_ingreso == "Mixto"
        assert table_row.sueldo_mensual == 1800.00
        assert table_row.activo is True

    def test_table_to_domain_jornalero(self):
        """Test converting JORNALERO type."""
        table_row = FamilyMemberTable(
            id=2,
            nombre="Pedro",
            tipo_ingreso="Jornalero",
            sueldo_mensual=None,
            activo=True,
        )
        member = family_member_to_domain(table_row)
        assert member.tipo_ingreso == IncomeType.JORNALERO

    def test_table_to_domain_ninguno(self):
        """Test converting NINGUNO type."""
        table_row = FamilyMemberTable(
            id=3,
            nombre="Ana",
            tipo_ingreso="Sin ingresos",
            sueldo_mensual=None,
            activo=True,
        )
        member = family_member_to_domain(table_row)
        assert member.tipo_ingreso == IncomeType.NINGUNO
