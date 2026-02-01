"""
Tests for FamilyMemberRepository.
"""
from datetime import date

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
            nombre="Juan",
            apellido="Pérez",
            fecha_nacimiento=date(1990, 5, 15),
            relacion="Padre",
        )
        result = repo.add(member)

        assert isinstance(result, Ok)
        assert result.ok_value.nombre == "Juan"
        assert result.ok_value.id is not None

    def test_get_all_family_members(self, repo):
        """Test getting all family members."""
        # Add members
        member1 = FamilyMember(nombre="Juan", apellido="Pérez", relacion="Padre")
        member2 = FamilyMember(nombre="María", apellido="Pérez", relacion="Madre")

        repo.add(member1)
        repo.add(member2)

        # Get all
        members = repo.get_all()
        assert len(members) >= 2
        assert any(m.nombre == "Juan" for m in members)
        assert any(m.nombre == "María" for m in members)

    def test_get_by_id(self, repo):
        """Test getting family member by id."""
        member = FamilyMember(nombre="Pedro", apellido="García", relacion="Hijo")
        created = repo.add(member)

        if created.is_ok():
            member_id = created.ok_value.id
            result = repo.get_by_id(member_id)

            assert isinstance(result, Ok)
            assert result.ok_value.nombre == "Pedro"

    def test_update_family_member(self, repo):
        """Test updating family member."""
        member = FamilyMember(nombre="Ana", apellido="López", relacion="Hija")
        created = repo.add(member)

        if created.is_ok():
            member_id = created.ok_value.id
            update_data = FamilyMember(
                id=member_id,
                nombre="Ana María",
                apellido="López",
                relacion="Hija",
            )
            result = repo.update(update_data)

            assert isinstance(result, Ok)
            assert result.ok_value.nombre == "Ana María"

    def test_delete_family_member(self, repo):
        """Test deleting family member (soft delete)."""
        member = FamilyMember(nombre="Carlos", apellido="Ruiz", relacion="Tío")
        created = repo.add(member)

        if created.is_ok():
            member_id = created.ok_value.id
            result = repo.delete(member_id)

            assert isinstance(result, Ok)
            # Verify it's marked as inactive (soft delete)
            get_result = repo.get_by_id(member_id)
            assert get_result.is_ok()
            assert get_result.ok_value.activo is False
