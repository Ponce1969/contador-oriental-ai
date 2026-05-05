"""
Modelos para compras en cuotas con tarjeta de crédito
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class InstallmentPurchase(BaseModel):
    """Compra en cuotas con tarjeta de crédito"""

    id: int | None = None
    expense_id: int | None = None
    familia_id: int

    # Datos de la compra
    nombre_tarjeta: str = Field(
        min_length=1,
        max_length=50,
        description="Nombre de la tarjeta (OCA, Scotia, etc.)",
    )
    monto_total: Decimal = Field(default=Decimal("0"), gt=0)
    numero_cuotas: int = Field(
        ge=1, le=48, description="Cantidad de cuotas (1 a 48)"
    )
    cuotas_pagadas: int = Field(default=0, ge=0)
    monto_por_cuota: Decimal = Field(default=Decimal("0"), ge=0)

    # Fechas
    fecha_compra: date = Field(default_factory=date.today)
    mes_inicio_pago: date | None = Field(
        default=None,
        description="Mes en que se paga la primera cuota (según cierre de tarjeta)",
    )
    fecha_ultima_cuota: date | None = None

    # Estado
    activo: bool = True
    completado: bool = False
    vectorizado: bool = False

    # Metadatos
    descripcion: str = Field(max_length=200)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def cuotas_restantes(self) -> int:
        return self.numero_cuotas - self.cuotas_pagadas_calculada

    @property
    def cuotas_pagadas_calculada(self) -> int:
        """
        Calcula las cuotas pagadas automáticamente según la fecha actual.
        Para tarjetas de crédito que se debitan automáticamente del banco.

        Si estamos EN el mes de inicio de pago, la primera cuota ya está
        en curso (se debita del resumen), así que cuenta como 1.
        """
        if self.mes_inicio_pago is None:
            return 0
        today = date.today()
        meses_desde_inicio = (
            (today.year - self.mes_inicio_pago.year) * 12
            + (today.month - self.mes_inicio_pago.month)
        )
        if meses_desde_inicio < 0:
            return 0
        return min(meses_desde_inicio + 1, self.numero_cuotas)

    @property
    def monto_restante(self) -> Decimal:
        return self.monto_total - (self.monto_por_cuota * self.cuotas_pagadas)


class InstallmentPayment(BaseModel):
    """Pago individual de una cuota"""

    id: int | None = None
    installment_purchase_id: int
    expense_id: int | None = None
    familia_id: int

    # Datos del pago
    numero_cuota: int = Field(ge=1, description="Número de cuota (1, 2, 3...)")
    monto_pagado: Decimal = Field(gt=0)
    fecha_pago: date = Field(default_factory=date.today)

    # Metadatos
    created_at: datetime | None = None


class InstallmentSummary(BaseModel):
    """Resumen de cuotas pendientes para el dashboard"""

    total_mes: Decimal = Field(
        default=Decimal("0"), description="Total a pagar este mes"
    )
    compras_pendientes: int = Field(
        default=0, description="Cantidad de compras con cuotas pendientes"
    )
    detalle: list[InstallmentPurchase] = Field(default_factory=list)
