"""
Tests for family_member_mappers.
"""

from database.tables import FamilyMemberTable
from models.family_member_model import FamilyMember
from repositories.family_member_mappers import (
    family_member_to_domain,
    family_member_to_table,
)


class TestFamilyMemberMappers:
    """Test cases for family member mappers."""

    def test_table_to_domain_persona(self):
        """Test converting table row (persona) to domain model."""
        table_row = FamilyMemberTable(
            id=1,
            nombre="Juan",
            tipo_miembro="persona",
            parentesco="padre",
            especie=None,
            edad=40,
            estado_laboral="empleado",
            activo=True,
            notas="Test notes",
        )
        member = family_member_to_domain(table_row)

        assert member.id == 1
        assert member.nombre == "Juan"
        assert member.tipo_miembro == "persona"
        assert member.parentesco == "padre"
        assert member.especie is None
        assert member.edad == 40
        assert member.estado_laboral == "empleado"
        assert member.activo is True

    def test_table_to_domain_mascota(self):
        """Test converting table row (mascota) to domain model."""
        table_row = FamilyMemberTable(
            id=2,
            nombre="Firulais",
            tipo_miembro="mascota",
            parentesco=None,
            especie="perro",
            edad=3,
            estado_laboral=None,
            activo=True,
        )
        member = family_member_to_domain(table_row)

        assert member.nombre == "Firulais"
        assert member.tipo_miembro == "mascota"
        assert member.especie == "perro"
        assert member.parentesco is None
        assert member.estado_laboral is None

    def test_domain_to_table_persona(self):
        """Test converting domain model (persona) to table row."""
        member = FamilyMember(
            nombre="María",
            tipo_miembro="persona",
            parentesco="madre",
            edad=38,
            estado_laboral="independiente",
            activo=True,
            notas="Notas de prueba",
        )
        table_row = family_member_to_table(member)

        assert table_row.nombre == "María"
        assert table_row.tipo_miembro == "persona"
        assert table_row.parentesco == "madre"
        assert table_row.edad == 38
        assert table_row.estado_laboral == "independiente"
        assert table_row.activo is True

    def test_domain_to_table_mascota(self):
        """Test converting domain model (mascota) to table row."""
        member = FamilyMember(
            nombre="Michi",
            tipo_miembro="mascota",
            especie="gato",
            edad=5,
            activo=True,
        )
        table_row = family_member_to_table(member)

        assert table_row.nombre == "Michi"
        assert table_row.tipo_miembro == "mascota"
        assert table_row.especie == "gato"
        assert table_row.parentesco is None

    def test_table_to_domain_campos_opcionales_none(self):
        """Test que los campos opcionales se mapean como None correctamente."""
        table_row = FamilyMemberTable(
            id=3,
            nombre="Ana",
            tipo_miembro="persona",
            activo=True,
        )
        member = family_member_to_domain(table_row)

        assert member.parentesco is None
        assert member.especie is None
        assert member.edad is None
        assert member.estado_laboral is None
        assert member.notas is None
