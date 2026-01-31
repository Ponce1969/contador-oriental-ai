"""
Modelo de Familia - Agrupación de usuarios
"""
from datetime import datetime

from pydantic import BaseModel, Field


class Family(BaseModel):
    """Familia - grupo de usuarios que comparten datos"""
    id: int | None = None
    nombre: str = Field(
        min_length=3,
        max_length=100,
        description="Nombre de la familia"
    )
    email: str | None = Field(
        default=None,
        max_length=100,
        description="Email de contacto"
    )
    activo: bool = Field(default=True, description="Familia activa")
    created_at: datetime | None = None
    
    def __str__(self) -> str:
        return self.nombre
