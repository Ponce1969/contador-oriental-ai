"""
Tests for email service.
"""

from unittest.mock import patch

import resend

from services.infrastructure.email_service import (
    MockEmailService,
    ResendEmailService,
)


class TestMockEmailService:
    """Test cases for MockEmailService."""

    def test_mock_email_service_sends(self):
        """Mock email service records sent emails."""
        mock_service = MockEmailService()

        result = mock_service.send_password_reset(
            to_email="test@example.com", reset_url="http://test.com/reset?token=abc"
        )

        assert result.is_ok()
        assert len(mock_service.sent_emails) == 1
        assert mock_service.sent_emails[0]["to"] == "test@example.com"
        assert (
            mock_service.sent_emails[0]["reset_url"]
            == "http://test.com/reset?token=abc"
        )


class TestResendEmailService:
    """Test cases for ResendEmailService."""

    @patch("services.infrastructure.email_service.os.getenv")
    def test_resend_email_service_success(self, mock_getenv):
        """Successful email sending via Resend."""
        mock_getenv.side_effect = lambda key, default=None: {
            "RESEND_API_KEY": "test_api_key",
            "RESEND_FROM_EMAIL": "test@example.com",
            "APP_BASE_URL": "http://test.com",
        }.get(key, default)

        with patch.object(resend, "api_key", "test_api_key"), patch.object(
            resend.Emails, "send", return_value={"id": "email_123"}
        ) as mock_send:
            service = ResendEmailService()
            result = service.send_password_reset(
                to_email="user@example.com",
                reset_url="http://test.com/reset?token=xyz",
            )

            assert result.is_ok()
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0][0]
            assert call_args["from"] == "test@example.com"
            assert call_args["to"] == ["user@example.com"]
            assert "Recuperá tu contraseña" in call_args["subject"]

    @patch("services.infrastructure.email_service.os.getenv")
    def test_resend_email_service_failure(self, mock_getenv):
        """Email sending failure via Resend."""
        mock_getenv.side_effect = lambda key, default=None: {
            "RESEND_API_KEY": "test_api_key",
            "RESEND_FROM_EMAIL": "test@example.com",
            "APP_BASE_URL": "http://test.com",
        }.get(key, default)

        with patch.object(
            resend.Emails,
            "send",
            side_effect=Exception("Resend API error"),
        ):
            service = ResendEmailService()
            result = service.send_password_reset(
                to_email="user@example.com",
                reset_url="http://test.com/reset?token=xyz",
            )

            assert result.is_err()
            assert "Error al enviar email" in result.err_value