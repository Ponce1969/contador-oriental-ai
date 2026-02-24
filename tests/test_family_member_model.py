"""
Tests for FamilyMember model.
"""

from models.family_member_model import FamilyMember


class TestFamilyMemberModel:
    """Test cases for FamilyMember model."""

    def test_family_member_creation_person(self):
        """Test basic person member creation."""
        member = FamilyMember(
            nombre="Juan Pérez",
            tipo_miembro="persona",
            parentesco="padre",
            edad=35,
            estado_laboral="empleado",
        )
        assert member.nombre == "Juan Pérez"
        assert member.tipo_miembro == "persona"
        assert member.parentesco == "padre"
        assert member.edad == 35
        assert member.activo is True

    def test_family_member_creation_pet(self):
        """Test pet member creation."""
        member = FamilyMember(
            nombre="Firulais",
            tipo_miembro="mascota",
            especie="perro",
            edad=3,
        )
        assert member.nombre == "Firulais"
        assert member.tipo_miembro == "mascota"
        assert member.especie == "perro"
        assert member.edad == 3

    def test_family_member_str_person(self):
        """Test string representation for person."""
        member = FamilyMember(
            nombre="María García",
            tipo_miembro="persona",
            parentesco="madre",
            edad=40
        )
        str_repr = str(member)
        assert "María García" in str_repr
        assert "madre" in str_repr
        assert "40 años" in str_repr

    def test_family_member_str_pet(self):
        """Test string representation for pet."""
        member = FamilyMember(
            nombre="Michi",
            tipo_miembro="mascota",
            especie="gato",
            edad=2
        )
        str_repr = str(member)
        assert "Michi" in str_repr
        assert "gato" in str_repr
        assert "2 años" in str_repr

    def test_family_member_default_values(self):
        """Test default values."""
        member = FamilyMember(nombre="Test")
        assert member.tipo_miembro == "persona"
        assert member.activo is True
        assert member.notas is None
        assert member.parentesco is None
        assert member.especie is None
        assert member.edad is None
        assert member.estado_laboral is None
