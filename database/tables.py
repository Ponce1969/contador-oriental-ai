from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

try:
    from pgvector.sqlalchemy import Vector as _Vector

    _VECTOR_TYPE = _Vector(768)
except Exception:
    _VECTOR_TYPE = Text

from database.base import Base


class FamiliaTable(Base):
    """
    Tabla de familias (multi-tenant)
    """

    __tablename__ = "familias"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(100), unique=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class FamilyMemberTable(Base):
    """
    Tabla de miembros de la familia
    Representa a las personas que conforman el núcleo familiar
    """

    __tablename__ = "family_members"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Relación con familia (multi-tenant)
    familia_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("familias.id"), nullable=False
    )

    # Datos básicos
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)

    # Tipo de miembro
    tipo_miembro: Mapped[str] = mapped_column(String(20), default="persona")

    # Parentesco (solo para personas)
    parentesco: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Especie (solo para mascotas)
    especie: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Edad
    edad: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Estado laboral (solo para personas)
    estado_laboral: Mapped[str | None] = mapped_column(String(50), nullable=True)

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
        Integer, ForeignKey("familias.id"), nullable=False
    )

    # Relación con miembro de la familia
    family_member_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("family_members.id"), nullable=False
    )

    # Datos básicos del ingreso
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    descripcion: Mapped[str] = mapped_column(String(200), nullable=False)

    # Categorización
    categoria: Mapped[str] = mapped_column(String(50), nullable=False)

    # Recurrencia
    es_recurrente: Mapped[bool] = mapped_column(Boolean, default=False)
    frecuencia: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Información adicional
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_incomes_familia_fecha", "familia_id", "fecha"),
        Index("idx_incomes_familia_categoria", "familia_id", "categoria"),
    )


class ExpenseTable(Base):
    """
    Tabla de gastos familiares
    Evolución de ShoppingItemTable para soportar todos los tipos de gastos
    """

    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Relación con familia (multi-tenant)
    familia_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("familias.id"), nullable=False
    )

    # Datos básicos del gasto
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
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

    # Estado de pago
    pendiente: Mapped[bool] = mapped_column(Boolean, default=False)

    # Compra en cuotas
    installment_purchase_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("installment_purchases.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Embedding semántico para búsqueda cosine via pgvector (Vector en PG, Text en otros)
    embedding = Column(_VECTOR_TYPE, nullable=True)

    # Campos OCR de ticket
    ticket_image_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_texto_crudo: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_confianza: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        Index("idx_expenses_familia_fecha", "familia_id", "fecha"),
        Index("idx_expenses_familia_categoria", "familia_id", "categoria"),
    )


# Alias para compatibilidad con código existente
ShoppingItemTable = ExpenseTable


class InstallmentPurchaseTable(Base):
    """
    Tabla de compras en cuotas con tarjeta de crédito
    """

    __tablename__ = "installment_purchases"

    id: Mapped[int] = mapped_column(primary_key=True)
    expense_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("expenses.id"), nullable=True
    )
    familia_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("familias.id"), nullable=False
    )

    nombre_tarjeta: Mapped[str] = mapped_column(String(50), nullable=False)
    monto_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    numero_cuotas: Mapped[int] = mapped_column(Integer, nullable=False)
    cuotas_pagadas: Mapped[int] = mapped_column(Integer, default=0)
    monto_por_cuota: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    fecha_compra: Mapped[date] = mapped_column(Date, nullable=False)
    mes_inicio_pago: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_ultima_cuota: Mapped[date | None] = mapped_column(Date, nullable=True)

    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    completado: Mapped[bool] = mapped_column(Boolean, default=False)
    vectorizado: Mapped[bool] = mapped_column(Boolean, default=False)

    descripcion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (
        Index("idx_installments_familia", "familia_id"),
        Index("idx_installments_activo", "familia_id", "activo"),
    )


class ExchangeRateTable(Base):
    """
    Tabla de cotizaciones de divisas (USD/UYU)
    """

    __tablename__ = "exchange_rates"

    id: Mapped[int] = mapped_column(primary_key=True)
    currency_pair: Mapped[str] = mapped_column(String(10), default="USD/UYU")
    rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class InstallmentPaymentTable(Base):
    """
    Tabla de pagos individuales de cada cuota
    """

    __tablename__ = "installment_payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    installment_purchase_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("installment_purchases.id", ondelete="CASCADE"),
        nullable=False,
    )
    expense_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("expenses.id"), nullable=True
    )
    familia_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("familias.id"), nullable=False
    )

    numero_cuota: Mapped[int] = mapped_column(Integer, nullable=False)
    monto_pagado: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fecha_pago: Mapped[date] = mapped_column(Date, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_payments_purchase", "installment_purchase_id"),
    )
