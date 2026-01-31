"""
Modelo de Usuario - Sistema de autenticación
"""
from datetime import datetime
from pydantic import BaseModel, Field


class User(BaseModel):
    """Usuario del sistema"""
    id: int | None = None
    familia_id: int = Field(gt=0, description="ID de la familia")
    username: str = Field(
        min_length=3,
        max_length=50,
        description="Nombre de usuario único"
    )
    password_hash: str = Field(description="Hash de la contraseña")
    nombre_completo: str | None = Field(
        default=None,
        max_length=100,
        description="Nombre completo del usuario"
    )
    activo: bool = Field(default=True, description="Usuario activo")
    created_at: datetime | None = None
    last_login: datetime | None = None
    
    def __str__(self) -> str:
        return f"{self.username} ({self.nombre_completo or 'Sin nombre'})"


class UserLogin(BaseModel):
    """Datos de login"""
    username: str = Field(min_length=3, description="Nombre de usuario")
    password: str = Field(min_length=6, description="Contraseña")


class UserCreate(BaseModel):
    """Crear nuevo usuario"""
    familia_id: int = Field(gt=0, description="ID de la familia")
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, description="Contraseña en texto plano")
    nombre_completo: str | None = None
