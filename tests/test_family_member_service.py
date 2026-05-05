"""
Tests for FamilyMemberService.
"""

import pytest
from result import Err, Ok

from models.errors import ValidationError
from models.family_member_model import FamilyMember


class TestFamilyMemberService:
    """Test cases for FamilyMemberService."""

    @pytest.fixture
    def service(self, db_session, setup_test_data):
        """Create family member service with test repository."""
        from repositories.family_member_repository import FamilyMemberRepository
        from services.domain.family_member_service import FamilyMemberService

        familia_id = setup_test_data["familia_id_1"]
        repo = FamilyMemberRepository(db_session, familia_id=familia_id)
        return FamilyMemberService(repo)

    def test_create_member_success(self, service):
        """Test successful member creation."""
        member = FamilyMember(
            nombre="Juan Pérez",
            tipo_miembro="persona",
            parentesco="padre",
            edad=35,
            estado_laboral="empleado",
        )
        result = service.create_member(member)

        assert isinstance(result, Ok)
        assert result.ok_value.nombre == "Juan Pérez"

    def test_create_member_empty_name(self, service):
        """Test creating member with empty/whitespace name fails."""
        member = FamilyMember(nombre="   ", tipo_miembro="persona", parentesco="padre")
        result = service.create_member(member)

        assert isinstance(result, Err)
        assert isinstance(result.err_value, ValidationError)
        assert "nombre" in result.err_value.message.lower()

    def test_create_pet_success(self, service):
        """Test creating pet member succeeds."""
        member = FamilyMember(
            nombre="Firulais", tipo_miembro="mascota", especie="perro", edad=3
        )
        result = service.create_member(member)

        assert isinstance(result, Ok)
        assert result.ok_value.tipo_miembro == "mascota"

    def test_list_members(self, service):
        """Test listing all members."""
        member1 = FamilyMember(
            nombre="Miembro1", tipo_miembro="persona", parentesco="padre"
        )
        member2 = FamilyMember(
            nombre="Miembro2", tipo_miembro="persona", parentesco="madre"
        )

        service.create_member(member1)
        service.create_member(member2)

        members = service.list_members()
        assert len(members) >= 2

    def test_list_active_members(self, service):
        """Test listing only active members."""
        member = FamilyMember(nombre="Activo", tipo_miembro="persona", parentesco="tío")
        created = service.create_member(member)

        if created.is_ok():
            active = service.list_active_members()
            assert len(active) >= 1

    def test_get_member(self, service):
        """Test getting member by id."""
        member = FamilyMember(
            nombre="Pedro", tipo_miembro="persona", parentesco="primo"
        )
        created = service.create_member(member)

        if created.is_ok():
            member_id = created.ok_value.id
            result = service.get_member(member_id)
            assert isinstance(result, Ok)
            assert result.ok_value.nombre == "Pedro"

    def test_update_member_success(self, service):
        """Test successful member update."""
        member = FamilyMember(
            nombre="Original", tipo_miembro="persona", parentesco="sobrino"
        )
        created = service.create_member(member)

        if created.is_ok():
            member_id = created.ok_value.id
            update_data = FamilyMember(
                id=member_id,
                nombre="Actualizado",
                tipo_miembro="persona",
                parentesco="sobrino",
            )
            result = service.update_member(update_data)
            assert isinstance(result, Ok)
            assert result.ok_value.nombre == "Actualizado"

    def test_update_member_without_id(self, service):
        """Test updating member without id fails."""
        member = FamilyMember(nombre="SinID", tipo_miembro="persona")
        result = service.update_member(member)

        assert isinstance(result, Err)
        assert isinstance(result.err_value, ValidationError)

    def test_update_member_empty_name(self, service):
        """Test updating member with whitespace name fails."""
        member = FamilyMember(nombre="Valid", tipo_miembro="persona")
        created = service.create_member(member)

        if created.is_ok():
            member_id = created.ok_value.id
            update_data = FamilyMember(
                id=member_id,
                nombre="   ",
                tipo_miembro="persona",
            )
            result = service.update_member(update_data)
            assert isinstance(result, Err)
            assert isinstance(result.err_value, ValidationError)

    def test_deactivate_member(self, service):
        """Test deactivating member."""
        member = FamilyMember(nombre="Desactivar", tipo_miembro="persona")
        created = service.create_member(member)

        if created.is_ok():
            member_id = created.ok_value.id
            result = service.deactivate_member(member_id)
            assert isinstance(result, Ok)

    def test_create_member_duplicate_name_fails(self, service):
        """Test creating member with duplicate name in same family fails."""
        member1 = FamilyMember(
            nombre="Micaela", tipo_miembro="persona", parentesco="hermana"
        )
        result1 = service.create_member(member1)
        assert result1.is_ok(), "First creation should succeed"

        member2 = FamilyMember(
            nombre="Micaela", tipo_miembro="persona", parentesco="prima"
        )
        result2 = service.create_member(member2)

        assert isinstance(result2, Err)
        assert isinstance(result2.err_value, ValidationError)
        assert "ya existe" in result2.err_value.message.lower()

    def test_update_member_duplicate_name_fails(self, service):
        """Test updating member to duplicate name in same family fails."""
        member1 = FamilyMember(
            nombre="Juan", tipo_miembro="persona", parentesco="hermano"
        )
        result1 = service.create_member(member1)
        assert result1.is_ok(), "First creation should succeed"

        member2 = FamilyMember(
            nombre="María", tipo_miembro="persona", parentesco="hermana"
        )
        result2 = service.create_member(member2)
        assert result2.is_ok(), "Second creation should succeed"

        existing_id = result1.ok_value.id
        update_data = FamilyMember(
            id=existing_id,
            nombre="María",
            tipo_miembro="persona",
            parentesco="hermano",
        )
        result3 = service.update_member(update_data)

        assert isinstance(result3, Err)
        assert isinstance(result3.err_value, ValidationError)
        assert "ya existe" in result3.err_value.message.lower()

    def test_update_member_same_name_succeeds(self, service):
        """Test updating member keeping same name succeeds."""
        member = FamilyMember(
            nombre="Pedro", tipo_miembro="persona", parentesco="tío"
        )
        created = service.create_member(member)
        assert created.is_ok(), "Creation should succeed"

        member_id = created.ok_value.id
        update_data = FamilyMember(
            id=member_id,
            nombre="Pedro",
            tipo_miembro="persona",
            parentesco="primo",
        )
        result = service.update_member(update_data)

        assert isinstance(result, Ok)
        assert result.ok_value.nombre == "Pedro"
        assert result.ok_value.parentesco == "primo"
