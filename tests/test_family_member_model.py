"""
Tests for FamilyMember model.
"""
import pytest

from models.family_member_model import FamilyMember, IncomeType


class TestFamilyMemberModel:
    """Test cases for FamilyMember model."""

    def test_family_member_creation(self):
        """Test basic family member creation."""
        member = FamilyMember(
            nombre="Juan",
            tipo_ingreso=IncomeType.FIJO,
            sueldo_mensual=2500.00,
        )
        assert member.nombre == "Juan"
        assert member.tipo_ingreso == IncomeType.FIJO
        assert member.sueldo_mensual == 2500.00
        assert member.activo is True

    def test_family_member_str(self):
        """Test string representation."""
        member = FamilyMember(nombre="María", tipo_ingreso=IncomeType.MIXTO)
        str_repr = str(member)
        assert "María" in str_repr
        assert "Mixto" in str_repr

    def test_tiene_sueldo_fijo_fijo(self):
        """Test tiene_sueldo_fijo for FIJO type."""
        member = FamilyMember(
            nombre="Pedro",
            tipo_ingreso=IncomeType.FIJO,
            sueldo_mensual=2000.00,
        )
        assert member.tiene_sueldo_fijo is True

    def test_tiene_sueldo_fijo_mixto(self):
        """Test tiene_sueldo_fijo for MIXTO type."""
        member = FamilyMember(
            nombre="Ana",
            tipo_ingreso=IncomeType.MIXTO,
            sueldo_mensual=1500.00,
        )
        assert member.tiene_sueldo_fijo is True

    def test_tiene_sueldo_fijo_jornalero(self):
        """Test tiene_sueldo_fijo for JORNALERO type."""
        member = FamilyMember(
            nombre="Luis",
            tipo_ingreso=IncomeType.JORNALERO,
        )
        assert member.tiene_sueldo_fijo is False

    def test_es_jornalero_jornalero(self):
        """Test es_jornalero for JORNALERO type."""
        member = FamilyMember(
            nombre="Carlos",
            tipo_ingreso=IncomeType.JORNALERO,
        )
        assert member.es_jornalero is True

    def test_es_jornalero_mixto(self):
        """Test es_jornalero for MIXTO type."""
        member = FamilyMember(
            nombre="Sofía",
            tipo_ingreso=IncomeType.MIXTO,
        )
        assert member.es_jornalero is True

    def test_es_jornalero_fijo(self):
        """Test es_jornalero for FIJO type."""
        member = FamilyMember(
            nombre="Diego",
            tipo_ingreso=IncomeType.FIJO,
        )
        assert member.es_jornalero is False

    def test_family_member_default_values(self):
        """Test default values."""
        member = FamilyMember(nombre="Test")
        assert member.tipo_ingreso == IncomeType.NINGUNO
        assert member.sueldo_mensual is None
        assert member.activo is True
        assert member.notas is None
