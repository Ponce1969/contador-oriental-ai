"""
Servicio de email para envío de mensajes transaccionales.
Provee una interfaz EmailService (Protocol) para testabilidad.
"""

from __future__ import annotations

import logging
import os
from typing import Protocol

from result import Err, Ok, Result

logger = logging.getLogger(__name__)


class EmailService(Protocol):
    """Interfaz de servicio de email para testabilidad"""

    def send_password_reset(self, to_email: str, reset_url: str) -> Result[None, str]:
        """Enviar email de reseteo de contraseña"""
        ...


class ResendEmailService:
    """Servicio de email usando la API de Resend"""

    def __init__(self) -> None:
        self._api_key = os.environ.get("RESEND_API_KEY") or None
        self._from_email = os.environ["RESEND_FROM_EMAIL"]
        self._base_url = os.environ["APP_BASE_URL"]

    def send_password_reset(self, to_email: str, reset_url: str) -> Result[None, str]:
        """Enviar email de reseteo de contraseña via Resend"""
        try:
            import resend

            resend.api_key = self._api_key

            resend.Emails.send(
                {
                    "from": self._from_email,
                    "to": [to_email],
                    "subject": "Recuperá tu contraseña — Contador Oriental",
                    "html": self._build_reset_email_html(reset_url),
                }
            )
            return Ok(None)
        except Exception as e:
            logger.error("Error sending password reset email: %s", str(e))
            return Err(f"Error al enviar email: {str(e)}")

    def _build_reset_email_html(self, reset_url: str) -> str:
        """Construir cuerpo HTML del email de reseteo"""
        button_style = (
            "display: inline-block; background-color: #1565C0; color: white; "
            "padding: 12px 24px; text-decoration: none; border-radius: 4px; "
            "margin: 16px 0;"
        )
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1565C0;">Recuperá tu contraseña</h2>
            <p>Recibimos una solicitud para resetear tu contraseña.</p>
            <p>Hacé click en el botón de abajo para crear una nueva contraseña:</p>
            <a href="{reset_url}" style="{button_style}">Reseteá tu contraseña</a>
            <p>Este link expira en 1 hora.</p>
            <p>Si no solicitaste este cambio, ignorá este email.</p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
            <p style="color: #999; font-size: 12px;">
                Contador Oriental — Auditor Familiar
            </p>
        </div>
        """


class MockEmailService:
    """Servicio de email mock para testing"""

    def __init__(self) -> None:
        self.sent_emails: list[dict] = []

    def send_password_reset(self, to_email: str, reset_url: str) -> Result[None, str]:
        self.sent_emails.append({"to": to_email, "reset_url": reset_url})
        return Ok(None)
