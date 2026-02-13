"""
Modelo de dominio para miembros de la familia
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FamilyMember(BaseModel):
    """
    Miembro de la familia
    Representa a cada persona o mascota que forma parte del núcleo familiar
    """
    id: int | None = None
    
    # Datos básicos
    nombre: str = Field(min_length=1, max_length=100, description="Nombre completo del miembro o mascota")
    
    # Tipo de miembro
    tipo_miembro: str = Field(
        default="persona",
        max_length=20,
        description="Tipo: persona o mascota"
    )
    
    # Parentesco (solo para personas)
    parentesco: str | None = Field(
        default=None,
        max_length=50,
        description="Parentesco: padre, madre, hijo, hija, abuelo, abuela, otro (solo personas)"
    )
    
    # Especie (solo para mascotas)
    especie: str | None = Field(
        default=None,
        max_length=50,
        description="Especie: gato, perro, pájaro, otro (solo mascotas)"
    )
    
    # Edad
    edad: int | None = Field(
        default=None,
        ge=0,
        le=150,
        description="Edad del miembro o mascota"
    )
    
    # Estado laboral (solo para personas)
    estado_laboral: str | None = Field(
        default=None,
        max_length=50,
        description="Estado laboral: empleado, desempleado, jubilado, estudiante, independiente (solo personas)"
    )
    
    # Estado
    activo: bool = Field(
        default=True,
        description="Indica si el miembro está activo en el sistema"
    )
    
    # Notas
    notas: str | None = Field(
        default=None,
        max_length=500,
        description="Notas adicionales sobre el miembro"
    )
    
    def __str__(self) -> str:
        edad_str = f"{self.edad} años" if self.edad else "edad no especificada"
        if self.tipo_miembro == "mascota":
            especie_str = self.especie if self.especie else "mascota"
            return f"{self.nombre} ({especie_str}, {edad_str})"
        else:
            parentesco_str = self.parentesco if self.parentesco else "otro"
            return f"{self.nombre} ({parentesco_str}, {edad_str})"
