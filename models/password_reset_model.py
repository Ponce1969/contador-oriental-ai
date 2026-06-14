"""
Modelo de token de reseteo de contraseña
"""

from datetime import datetime

from pydantic import BaseModel, Field


class PasswordResetToken(BaseModel):
    """Token para resetear contraseña"""

    id: int | None = None
    user_id: int = Field(gt=0, description="ID del usuario")
    token: str = Field(description="Token criptográfico de reseteo")
    expires_at: datetime = Field(description="Fecha de expiración del token")
    used_at: datetime | None = Field(
        default=None, description="Fecha de uso, None si no fue usado"
    )
    created_at: datetime | None = None
