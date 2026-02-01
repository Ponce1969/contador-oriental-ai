"""
Tests for User model.
"""

from datetime import datetime

import pytest

from models.user_model import User, UserCreate, UserLogin


class TestUserModel:
    """Test cases for User model."""

    def test_user_creation_basic(self):
        """Test basic user creation."""
        user = User(
            familia_id=1,
            username="testuser",
            password_hash="hashed_pass",
            nombre_completo="Test User",
        )

        assert user.username == "testuser"
        assert user.nombre_completo == "Test User"
        assert user.familia_id == 1
        assert user.activo is True

    def test_user_creation_full(self, sample_user_data):
        """Test user creation with all fields."""
        user = User(**sample_user_data)

        assert user.username == "testuser"
        assert user.nombre_completo == "Usuario de Prueba"
        assert user.activo is True

    def test_user_default_values(self):
        """Test default values for user."""
        user = User(
            familia_id=1,
            username="testuser",
            password_hash="hash",
        )

        assert user.activo is True
        assert user.nombre_completo is None
        assert user.id is None
        assert user.created_at is None
        assert user.last_login is None

    def test_user_timestamps(self):
        """Test user with timestamps."""
        now = datetime.now()
        user = User(
            id=1,
            familia_id=1,
            username="testuser",
            password_hash="hash",
            created_at=now,
            last_login=now,
        )

        assert user.id == 1
        assert user.created_at == now
        assert user.last_login == now

    def test_user_inactive(self):
        """Test inactive user creation."""
        user = User(
            familia_id=1,
            username="inactive",
            password_hash="hash",
            activo=False,
        )

        assert user.activo is False


class TestUserCreate:
    """Test cases for UserCreate DTO."""

    def test_user_create_basic(self):
        """Test UserCreate creation."""
        user_create = UserCreate(
            familia_id=1,
            username="newuser",
            password="password123",
            nombre_completo="New User",
        )

        assert user_create.username == "newuser"
        assert user_create.password == "password123"


class TestUserLogin:
    """Test cases for UserLogin DTO."""

    def test_user_login_creation(self):
        """Test UserLogin creation."""
        login = UserLogin(
            username="testuser",
            password="password123",
        )

        assert login.username == "testuser"
        assert login.password == "password123"

    def test_user_login_validation(self):
        """Test UserLogin validation."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            UserLogin(
                username="",
                password="password",
            )
