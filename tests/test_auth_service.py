"""
Tests for AuthService.
"""
import pytest
from result import Err, Ok

from models.errors import ValidationError
from models.user_model import UserCreate, UserLogin
from services.auth_service import AuthService


class TestAuthService:
    """Test cases for AuthService."""

    @pytest.fixture
    def service(self, db_session):
        """Create auth service with test repository."""
        from repositories.user_repository import UserRepository
        repo = UserRepository(session=db_session)
        return AuthService(repo)

    def test_create_user_success(self, service):
        """Test successful user creation."""
        user_data = UserCreate(
            familia_id=1,
            username="newuser",
            password="password123",
            nombre_completo="New User",
        )
        result = service.create_user(user_data)

        assert isinstance(result, Ok)
        assert result.ok_value.username == "newuser"

    def test_create_user_duplicate_username(self, service):
        """Test creating user with duplicate username fails."""
        user_data = UserCreate(
            familia_id=1,
            username="duplicate",
            password="password123",
            nombre_completo="First User",
        )
        service.create_user(user_data)

        # Try to create another with same username
        user_data2 = UserCreate(
            familia_id=1,
            username="duplicate",
            password="password456",
            nombre_completo="Second User",
        )
        result = service.create_user(user_data2)

        assert isinstance(result, Err)
        assert isinstance(result.err_value, ValidationError)

    def test_login_success(self, service):
        """Test successful login."""
        # First create a user
        user_data = UserCreate(
            familia_id=1,
            username="logintest",
            password="password123",
            nombre_completo="Login Test",
        )
        service.create_user(user_data)

        # Then login
        credentials = UserLogin(
            username="logintest",
            password="password123",
        )
        result = service.login(credentials)

        assert isinstance(result, Ok)
        assert result.ok_value.username == "logintest"

    def test_login_wrong_password(self, service):
        """Test login with wrong password fails."""
        # Create user
        user_data = UserCreate(
            familia_id=1,
            username="wrongpass",
            password="correctpass",
            nombre_completo="Wrong Pass Test",
        )
        service.create_user(user_data)

        # Try to login with wrong password
        credentials = UserLogin(
            username="wrongpass",
            password="wrongpassword",
        )
        result = service.login(credentials)

        assert isinstance(result, Err)
        assert isinstance(result.err_value, ValidationError)

    def test_login_nonexistent_user(self, service):
        """Test login with non-existent user fails."""
        credentials = UserLogin(
            username="nonexistent",
            password="password123",
        )
        result = service.login(credentials)

        assert isinstance(result, Err)
        assert isinstance(result.err_value, ValidationError)

    def test_change_password_success(self, service):
        """Test successful password change."""
        # Create user
        user_data = UserCreate(
            familia_id=1,
            username="changepass",
            password="oldpassword",
            nombre_completo="Change Pass",
        )
        created = service.create_user(user_data)

        if created.is_ok():
            user_id = created.ok_value.id
            result = service.change_password(
                user_id,
                "oldpassword",
                "newpassword123",
            )

            assert isinstance(result, Ok)

    def test_change_password_wrong_old(self, service):
        """Test password change with wrong old password fails."""
        # Create user
        user_data = UserCreate(
            familia_id=1,
            username="wrongold",
            password="correctold",
            nombre_completo="Wrong Old",
        )
        created = service.create_user(user_data)

        if created.is_ok():
            user_id = created.ok_value.id
            result = service.change_password(
                user_id,
                "wrongoldpass",
                "newpassword123",
            )

            assert isinstance(result, Err)
            assert isinstance(result.err_value, ValidationError)
