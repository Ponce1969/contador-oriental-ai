"""
Tests for AuthService.
"""

from datetime import UTC, datetime, timedelta

import pytest
from result import Err, Ok

from models.errors import ValidationError
from models.user_model import UserCreate, UserLogin
from services.domain.auth_service import AuthService
from services.infrastructure.email_service import MockEmailService


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


class TestPasswordReset:
    """Test cases for password reset functionality."""

    @pytest.fixture
    def service_with_mock_email(self, db_session):
        """Create auth service with mock email service for testing."""
        from repositories.user_repository import UserRepository

        repo = UserRepository(session=db_session)
        service = AuthService(repo)
        mock_email = MockEmailService()
        service.set_email_service(mock_email)
        return service

    @pytest.fixture
    def user_with_email(self, db_session):
        """Create a test user with email."""
        from argon2 import PasswordHasher

        ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)
        password_hash = ph.hash("testpassword")

        result = db_session.execute(
            """
            INSERT INTO usuarios
                (familia_id, username, password_hash, nombre_completo, email, activo)
            VALUES (1, 'resetemailuser', :password_hash, 'Reset Email User',
                    'test@example.com', true)
            RETURNING id
            """,
            {"password_hash": password_hash},
        )
        db_session.flush()
        return result.scalar()

    def test_request_password_reset_existing_email(
        self, service_with_mock_email, user_with_email
    ):
        """Password reset request for existing email creates token and sends."""
        result = service_with_mock_email.request_password_reset("test@example.com")

        assert result.is_ok()
        assert "Si tu email está registrado" in result.ok_value

        # Verify email was sent
        email_service = service_with_mock_email._email_service
        assert len(email_service.sent_emails) == 1
        assert email_service.sent_emails[0]["to"] == "test@example.com"
        assert "/reset-password?token=" in email_service.sent_emails[0]["reset_url"]

    def test_request_password_reset_nonexistent_email(
        self, service_with_mock_email
    ):
        """Non-existent email returns generic message (enum protection)."""
        result = service_with_mock_email.request_password_reset(
            "nonexistent@example.com"
        )

        assert result.is_ok()
        # Should return generic success message (email enumeration protection)
        assert "Si tu email está registrado" in result.ok_value

        # No email should be sent
        email_service = service_with_mock_email._email_service
        assert len(email_service.sent_emails) == 0

    def test_request_password_reset_rate_limited(
        self, service_with_mock_email, user_with_email
    ):
        """Test password reset rate limiting."""
        from core.security import rate_limiter

        # Exhaust rate limit for this email (5 failures = blocked)
        email = "test@example.com"
        for _ in range(5):
            rate_limiter.registrar_fallo(f"reset_{email}")

        # Now should be rate limited
        result = service_with_mock_email.request_password_reset(email)

        assert result.is_ok()
        assert "Esperá" in result.ok_value

    def test_reset_password_valid_token(
        self, service_with_mock_email, user_with_email
    ):
        """Reset password with valid token succeeds."""
        from repositories.password_reset_repository import PasswordResetRepository

        # Create a valid token
        reset_repo = PasswordResetRepository(
            session=service_with_mock_email._user_repo._session,
        )
        token = "valid_reset_token_123"
        expires_at = datetime.now(UTC) + timedelta(hours=1)
        reset_repo.create_token(
            user_id=user_with_email,
            token=token,
            expires_at=expires_at,
        )

        # Reset password
        result = service_with_mock_email.reset_password(token, "newpassword123")

        assert result.is_ok()

    def test_reset_password_expired_token(
        self, service_with_mock_email, user_with_email
    ):
        """Reset password with expired token fails."""
        from repositories.password_reset_repository import PasswordResetRepository

        # Create an expired token
        reset_repo = PasswordResetRepository(
            session=service_with_mock_email._user_repo._session,
        )
        token = "expired_reset_token_456"
        expires_at = datetime.now(UTC) - timedelta(hours=1)  # Expired
        reset_repo.create_token(
            user_id=user_with_email,
            token=token,
            expires_at=expires_at,
        )

        # Try to reset password
        result = service_with_mock_email.reset_password(token, "newpassword123")

        assert result.is_err()
        assert "inválido o expirado" in str(result.err_value.message)

    def test_reset_password_used_token(
        self, service_with_mock_email, user_with_email
    ):
        """Reset password with already used token fails."""
        from repositories.password_reset_repository import PasswordResetRepository

        # Create and mark token as used
        reset_repo = PasswordResetRepository(
            session=service_with_mock_email._user_repo._session,
        )
        token = "used_reset_token_789"
        expires_at = datetime.now(UTC) + timedelta(hours=1)
        create_result = reset_repo.create_token(
            user_id=user_with_email,
            token=token,
            expires_at=expires_at,
        )
        reset_repo.mark_used(create_result.ok_value.id)

        # Try to reset password
        result = service_with_mock_email.reset_password(token, "newpassword123")

        assert result.is_err()
        assert "inválido o expirado" in str(result.err_value.message)

    def test_reset_password_invalid_token(self, service_with_mock_email):
        """Reset password with non-existent token fails."""
        result = service_with_mock_email.reset_password(
            "nonexistent_token", "newpassword123",
        )

        assert result.is_err()
        assert "inválido o expirado" in str(result.err_value.message)

    def test_reset_password_short_password(
        self, service_with_mock_email, user_with_email
    ):
        """Reset password with too short password fails."""
        from repositories.password_reset_repository import PasswordResetRepository

        # Create a valid token
        reset_repo = PasswordResetRepository(
            session=service_with_mock_email._user_repo._session,
        )
        token = "short_pass_token"
        expires_at = datetime.now(UTC) + timedelta(hours=1)
        reset_repo.create_token(
            user_id=user_with_email,
            token=token,
            expires_at=expires_at,
        )

        # Try to reset with short password
        result = service_with_mock_email.reset_password(token, "123")

        assert result.is_err()
        assert "al menos 6 caracteres" in str(result.err_value.message)
