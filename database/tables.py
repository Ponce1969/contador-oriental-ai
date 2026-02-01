from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class FamilyMemberTable(Base):
    """
    Tabla de miembros de la familia
    """
    __tablename__ = "family_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Relación con familia (multi-tenant)
    familia_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("familias.id"),
        nullable=False
    )
    
    # Datos básicos
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Tipo de ingreso
    tipo_ingreso: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Sueldo mensual fijo (si aplica)
    sueldo_mensual: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Estado
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Notas
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)


class IncomeTable(Base):
    """
    Tabla de ingresos familiares
    """
    __tablename__ = "incomes"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Relación con familia (multi-tenant)
    familia_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("familias.id"),
        nullable=False
    )
    
    # Relación con miembro de la familia
    family_member_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("family_members.id"),
        nullable=False
    )
    
    # Datos básicos del ingreso
    monto: Mapped[float] = mapped_column(Float, nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    descripcion: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # Categorización
    categoria: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Recurrencia
    es_recurrente: Mapped[bool] = mapped_column(Boolean, default=False)
    frecuencia: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Información adicional
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)


class ExpenseTable(Base):
    """
    Tabla de gastos familiares
    Evolución de ShoppingItemTable para soportar todos los tipos de gastos
    """
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Relación con familia (multi-tenant)
    familia_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("familias.id"),
        nullable=False
    )
    
    # Datos básicos del gasto
    monto: Mapped[float] = mapped_column(Float, nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    descripcion: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # Categorización
    categoria: Mapped[str] = mapped_column(String(50), nullable=False)
    subcategoria: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Información de pago
    metodo_pago: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Recurrencia
    es_recurrente: Mapped[bool] = mapped_column(Boolean, default=False)
    frecuencia: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Información adicional
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Campos legacy de ShoppingItem (para migración)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    purchased: Mapped[bool] = mapped_column(Boolean, default=False)
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)


# Alias para compatibilidad con código existente
ShoppingItemTable = ExpenseTable
