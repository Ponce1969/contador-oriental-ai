"""
Tests for PasswordResetRepository.
"""

from datetime import UTC, datetime, timedelta

import pytest

from repositories.password_reset_repository import PasswordResetRepository


class TestPasswordResetRepository:
    """Test cases for PasswordResetRepository."""

    @pytest.fixture
    def repo(self, db_session):
        """Create password reset repository with test session."""
        return PasswordResetRepository(session=db_session)

    @pytest.fixture
    def user_id(self, db_session):
        """Create a test user and return its ID."""
        from argon2 import PasswordHasher

        ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)
        password_hash = ph.hash("testpassword")

        result = db_session.execute(
            """
            INSERT INTO usuarios
                (familia_id, username, password_hash, nombre_completo, activo)
            VALUES (1, 'resetuser', :password_hash, 'Reset User', true)
            RETURNING id
            """,
            {"password_hash": password_hash},
        )
        db_session.flush()
        return result.scalar()

    def test_create_token_success(self, repo, user_id):
        """Test successful token creation."""
        token = "test_token_123"
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        result = repo.create_token(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
        )

        assert result.is_ok()
        reset_token = result.ok_value
        assert reset_token.token == token
        assert reset_token.user_id == user_id
        assert reset_token.used_at is None

    def test_find_valid_token_success(self, repo, user_id):
        """Test finding a valid token."""
        token = "valid_token_456"
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        # Create token
        repo.create_token(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
        )

        # Find it
        result = repo.find_valid_token(token)

        assert result.is_ok()
        reset_token = result.ok_value
        assert reset_token is not None
        assert reset_token.token == token
        assert reset_token.user_id == user_id

    def test_find_valid_token_expired(self, repo, user_id):
        """Test finding an expired token returns None."""
        token = "expired_token_789"
        expires_at = datetime.now(UTC) - timedelta(hours=1)  # Already expired

        # Create expired token
        repo.create_token(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
        )

        # Try to find it
        result = repo.find_valid_token(token)

        assert result.is_ok()
        assert result.ok_value is None

    def test_find_valid_token_used(self, repo, user_id):
        """Test finding a used token returns None."""
        token = "used_token_101"
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        # Create token
        create_result = repo.create_token(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
        )
        reset_token = create_result.ok_value

        # Mark as used
        repo.mark_used(reset_token.id)

        # Try to find it
        result = repo.find_valid_token(token)

        assert result.is_ok()
        assert result.ok_value is None

    def test_find_valid_token_nonexistent(self, repo):
        """Test finding a non-existent token returns None."""
        result = repo.find_valid_token("nonexistent_token")

        assert result.is_ok()
        assert result.ok_value is None

    def test_mark_used_success(self, repo, user_id):
        """Test marking a token as used."""
        token = "mark_used_token"
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        # Create token
        create_result = repo.create_token(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
        )
        reset_token = create_result.ok_value

        # Mark as used
        mark_result = repo.mark_used(reset_token.id)

        assert mark_result.is_ok()

        # Verify it's marked
        find_result = repo.find_valid_token(token)
        assert find_result.ok_value is None
