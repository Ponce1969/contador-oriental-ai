"""
Modelos de dominio para el AI Contador Oriental
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class KnowledgeFile(str, Enum):
    """Archivos de conocimiento disponibles"""
    INCLUSION_FINANCIERA = "inclusion_financiera_uy.md"
    IRPF_FAMILIA = "irpf_familia_uy.md"
    AHORRO_UI = "ahorro_ui_uy.md"


class ChatMessage(BaseModel):
    """Mensaje en el chat con el Contador Oriental"""
    role: str = Field(description="Rol del mensaje: 'user' o 'assistant'")
    content: str = Field(description="Contenido del mensaje")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def __str__(self) -> str:
        return f"[{self.role}] {self.content[:50]}..."


class AIRequest(BaseModel):
    """Request para el Contador Oriental"""
    pregunta: str = Field(min_length=1, description="Pregunta del usuario")
    familia_id: int = Field(description="ID de la familia consultante")
    incluir_gastos_recientes: bool = Field(
        default=True,
        description="Si incluir gastos recientes en el contexto"
    )
    
    def __str__(self) -> str:
        return (
            f"AIRequest(familia={self.familia_id}, "
            f"pregunta='{self.pregunta[:30]}...')"
        )


class AIContext(BaseModel):
    """Contexto financiero pre-calculado por Python para el Contador Oriental.
    Gemma solo lee estos valores, nunca los calcula.
    """
    resumen_gastos: dict = Field(
        default_factory=dict,
        description="Gastos agrupados por categoría y descripción con totales"
    )
    total_gastos_count: int = Field(
        default=0,
        description="Cantidad de transacciones en el filtro actual"
    )
    total_gastos_mes: float = Field(
        default=0.0,
        description="Total de gastos del mes completo (todas las categorías)"
    )
    ingresos_total: float = Field(
        default=0.0,
        description="Total de ingresos del mes"
    )
    miembros_count: int = Field(
        default=0,
        description="Cantidad de miembros en la familia"
    )
    resumen_metodos_pago: str = Field(
        default="",
        description="Resumen de métodos de pago usados en el mes (ej: Efectivo: 6, Tarjeta débito: 1)"
    )


class AIResponse(BaseModel):
    """Respuesta del Contador Oriental"""
    respuesta: str = Field(description="Respuesta generada por el modelo")
    archivo_usado: str | None = Field(
        default=None,
        description="Archivo de conocimiento usado como contexto"
    )
    gastos_incluidos: int = Field(
        default=0,
        description="Cantidad de gastos incluidos en el contexto"
    )
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def __str__(self) -> str:
        return (
            f"AIResponse(archivo={self.archivo_usado}, "
            f"gastos={self.gastos_incluidos})"
        )
