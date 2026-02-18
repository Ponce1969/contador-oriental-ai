"""
Tests for FamilyMemberRepository.
"""
import pytest
from result import Ok

from models.family_member_model import FamilyMember


class TestFamilyMemberRepository:
    """Test cases for FamilyMemberRepository."""

    @pytest.fixture
    def repo(self, db_session):
        """Create family member repository with test session."""
        from repositories.family_member_repository import FamilyMemberRepository
        return FamilyMemberRepository(db_session, familia_id=1)

    def test_add_family_member(self, repo):
        """Test adding a family member."""
        member = FamilyMember(
            nombre="Juan Pérez",
            tipo_miembro="persona",
            parentesco="padre",
            edad=34,
        )
        result = repo.add(member)

        assert isinstance(result, Ok)
        assert result.ok_value.nombre == "Juan Pérez"
        assert result.ok_value.id is not None

    def test_get_all_family_members(self, repo):
        """Test getting all family members."""
        # Add members
        member1 = FamilyMember(nombre="Juan Pérez", tipo_miembro="persona", parentesco="padre")
        member2 = FamilyMember(nombre="María Pérez", tipo_miembro="persona", parentesco="madre")

        repo.add(member1)
        repo.add(member2)

        # Get all
        members = repo.get_all()
        assert len(members) >= 2
        assert any(m.nombre == "Juan Pérez" for m in members)
        assert any(m.nombre == "María Pérez" for m in members)

    def test_get_by_id(self, repo):
        """Test getting family member by id."""
        member = FamilyMember(nombre="Pedro García", tipo_miembro="persona", parentesco="hijo")
        created = repo.add(member)

        if created.is_ok():
            member_id = created.ok_value.id
            result = repo.get_by_id(member_id)

            assert isinstance(result, Ok)
            assert result.ok_value.nombre == "Pedro García"

    def test_update_family_member(self, repo):
        """Test updating family member."""
        member = FamilyMember(nombre="Ana López", tipo_miembro="persona", parentesco="hija")
        created = repo.add(member)

        if created.is_ok():
            member_id = created.ok_value.id
            update_data = FamilyMember(
                id=member_id,
                nombre="Ana María López",
                tipo_miembro="persona",
                parentesco="hija",
            )
            result = repo.update(update_data)

            assert isinstance(result, Ok)
            assert result.ok_value.nombre == "Ana María López"

    def test_delete_family_member(self, repo):
        """Test deleting family member (soft delete)."""
        member = FamilyMember(nombre="Carlos Ruiz", tipo_miembro="persona", parentesco="tío")
        created = repo.add(member)

        if created.is_ok():
            member_id = created.ok_value.id
            result = repo.delete(member_id)

            assert isinstance(result, Ok)
            # Verify it's marked as inactive (soft delete)
            get_result = repo.get_by_id(member_id)
            assert get_result.is_ok()
            assert get_result.ok_value.activo is False
