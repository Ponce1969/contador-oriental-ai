"""
Tests for FamilyMemberService.
"""
import pytest
from result import Err, Ok

from models.family_member_model import FamilyMember, IncomeType
from models.errors import ValidationError


class TestFamilyMemberService:
    """Test cases for FamilyMemberService."""

    @pytest.fixture
    def service(self, db_session):
        """Create family member service with test repository."""
        from repositories.family_member_repository import FamilyMemberRepository
        from services.family_member_service import FamilyMemberService
        repo = FamilyMemberRepository(db_session, familia_id=1)
        return FamilyMemberService(repo)

    def test_create_member_success(self, service):
        """Test successful member creation."""
        member = FamilyMember(nombre="Juan", apellido="Pérez", relacion="Padre")
        result = service.create_member(member)

        assert isinstance(result, Ok)
        assert result.ok_value.nombre == "Juan"

    def test_create_member_empty_name(self, service):
        """Test creating member with empty/whitespace name fails."""
        # Use a name that passes Pydantic but fails business validation
        member = FamilyMember(nombre="   ", apellido="Pérez", relacion="Padre")
        result = service.create_member(member)

        assert isinstance(result, Err)
        assert isinstance(result.err_value, ValidationError)
        assert "nombre" in result.err_value.message.lower()

    def test_create_member_fijo_without_sueldo(self, service):
        """Test creating FIJO member without sueldo fails."""
        member = FamilyMember(
            nombre="María",
            apellido="García",
            relacion="Madre",
            tipo_ingreso=IncomeType.FIJO,
            sueldo_mensual=None,
        )
        result = service.create_member(member)

        assert isinstance(result, Err)
        assert isinstance(result.err_value, ValidationError)
        assert "sueldo" in result.err_value.message.lower()

    def test_create_member_fijo_with_sueldo(self, service):
        """Test creating FIJO member with sueldo succeeds."""
        member = FamilyMember(
            nombre="Carlos",
            apellido="López",
            relacion="Hijo",
            tipo_ingreso=IncomeType.FIJO,
            sueldo_mensual=2500.00,
        )
        result = service.create_member(member)

        assert isinstance(result, Ok)
        assert result.ok_value.sueldo_mensual == 2500.00

    def test_create_member_mixto_without_sueldo(self, service):
        """Test creating MIXTO member without sueldo fails."""
        member = FamilyMember(
            nombre="Ana",
            apellido="Ruiz",
            relacion="Hija",
            tipo_ingreso=IncomeType.MIXTO,
            sueldo_mensual=0,
        )
        result = service.create_member(member)

        assert isinstance(result, Err)
        assert isinstance(result.err_value, ValidationError)

    def test_list_members(self, service):
        """Test listing all members."""
        member1 = FamilyMember(nombre="Miembro1", relacion="Padre")
        member2 = FamilyMember(nombre="Miembro2", relacion="Madre")

        service.create_member(member1)
        service.create_member(member2)

        members = service.list_members()
        assert len(members) >= 2

    def test_list_active_members(self, service):
        """Test listing only active members."""
        member = FamilyMember(nombre="Activo", relacion="Tío")
        created = service.create_member(member)

        if created.is_ok():
            active = service.list_active_members()
            assert len(active) >= 1

    def test_get_member(self, service):
        """Test getting member by id."""
        member = FamilyMember(nombre="Pedro", relacion="Primo")
        created = service.create_member(member)

        if created.is_ok():
            member_id = created.ok_value.id
            result = service.get_member(member_id)
            assert isinstance(result, Ok)
            assert result.ok_value.nombre == "Pedro"

    def test_update_member_success(self, service):
        """Test successful member update."""
        member = FamilyMember(nombre="Original", relacion="Sobrino")
        created = service.create_member(member)

        if created.is_ok():
            member_id = created.ok_value.id
            update_data = FamilyMember(
                id=member_id,
                nombre="Actualizado",
                relacion="Sobrino",
            )
            result = service.update_member(update_data)
            assert isinstance(result, Ok)
            assert result.ok_value.nombre == "Actualizado"

    def test_update_member_without_id(self, service):
        """Test updating member without id fails."""
        member = FamilyMember(nombre="SinID", relacion="Test")
        result = service.update_member(member)

        assert isinstance(result, Err)
        assert isinstance(result.err_value, ValidationError)

    def test_update_member_empty_name(self, service):
        """Test updating member with whitespace name fails."""
        member = FamilyMember(nombre="Valid", relacion="Test")
        created = service.create_member(member)

        if created.is_ok():
            member_id = created.ok_value.id
            # Use whitespace that passes Pydantic but fails business validation
            update_data = FamilyMember(
                id=member_id,
                nombre="   ",
                relacion="Test",
            )
            result = service.update_member(update_data)
            assert isinstance(result, Err)
            assert isinstance(result.err_value, ValidationError)

    def test_deactivate_member(self, service):
        """Test deactivating member."""
        member = FamilyMember(nombre="Desactivar", relacion="Test")
        created = service.create_member(member)

        if created.is_ok():
            member_id = created.ok_value.id
            result = service.deactivate_member(member_id)
            assert isinstance(result, Ok)

    def test_create_member_mixto_with_sueldo(self, service):
        """Test creating MIXTO member with sueldo succeeds."""
        member = FamilyMember(
            nombre="Luis",
            apellido="Martínez",
            relacion="Hijo",
            tipo_ingreso=IncomeType.MIXTO,
            sueldo_mensual=1800.00,
        )
        result = service.create_member(member)

        assert isinstance(result, Ok)
        assert result.ok_value.tipo_ingreso == IncomeType.MIXTO

    def test_create_member_variable_without_sueldo(self, service):
        """Test creating JORNALERO member without sueldo succeeds."""
        member = FamilyMember(
            nombre="Pedro",
            apellido="Sánchez",
            relacion="Tío",
            tipo_ingreso=IncomeType.JORNALERO,
            sueldo_mensual=None,
        )
        result = service.create_member(member)

        assert isinstance(result, Ok)
        assert result.ok_value.tipo_ingreso == IncomeType.JORNALERO
