"""
Modelo de dominio para gastos familiares
Evolución de ShoppingItem a un sistema completo de gastos
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from models.categories import ExpenseCategory, PaymentMethod, RecurrenceFrequency


class Expense(BaseModel):
    """
    Gasto familiar - modelo completo para cualquier tipo de gasto
    """
    id: int | None = None
    
    # Datos básicos del gasto
    monto: float = Field(gt=0, description="Monto del gasto en pesos")
    fecha: date = Field(default_factory=date.today, description="Fecha del gasto")
    descripcion: str = Field(min_length=1, max_length=200, description="Descripción del gasto")
    
    # Categorización
    categoria: ExpenseCategory = Field(description="Categoría principal del gasto")
    subcategoria: str | None = Field(default=None, description="Subcategoría específica")
    
    # Información de pago
    metodo_pago: PaymentMethod = Field(
        default=PaymentMethod.EFECTIVO,
        description="Método de pago utilizado"
    )
    
    # Recurrencia
    es_recurrente: bool = Field(
        default=False,
        description="Indica si es un gasto recurrente"
    )
    frecuencia: RecurrenceFrequency | None = Field(
        default=None,
        description="Frecuencia del gasto recurrente"
    )
    
    # Información adicional
    notas: str | None = Field(
        default=None,
        max_length=500,
        description="Notas adicionales sobre el gasto"
    )
    
    # Campos heredados de ShoppingItem (para compatibilidad temporal)
    # TODO: Migrar datos existentes y eliminar estos campos
    name: str | None = None
    price: float | None = None
    category: str | None = None
    purchased: bool = False
    purchase_date: date | None = None
    
    def __str__(self) -> str:
        return f"{self.categoria.value} - {self.descripcion}: ${self.monto:.2f}"
    
    @property
    def categoria_nombre(self) -> str:
        """Nombre de la categoría sin emoji"""
        return self.categoria.value.split(" ", 1)[1] if " " in self.categoria.value else self.categoria.value
