"""
Service para gestión de compras en cuotas
"""
from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from result import Err, Result

from models.errors import DatabaseError, ValidationError
from models.expense_model import Expense
from models.installment_model import InstallmentPayment, InstallmentPurchase
from repositories.expense_repository import ExpenseRepository
from repositories.installment_repository import (
    InstallmentPaymentRepository,
    InstallmentPurchaseRepository,
)


def _add_months(source_date: date, months: int) -> date:
    """Agregar meses a una fecha (aproximación de 30 días)"""
    month = source_date.month + months - 1
    year = source_date.year + month // 12
    month = month % 12 + 1
    day = min(source_date.day, 28)  # Evitar fechas inválidas como 31 de febrero
    return date(year, month, day)


class InstallmentService:
    """Lógica de negocio para compras en cuotas"""

    def __init__(
        self,
        purchase_repo: InstallmentPurchaseRepository,
        payment_repo: InstallmentPaymentRepository,
        expense_repo: ExpenseRepository | None = None,
    ) -> None:
        self._purchase_repo = purchase_repo
        self._payment_repo = payment_repo
        self._expense_repo = expense_repo

    def create_installment(
        self,
        expense: Expense,
        nombre_tarjeta: str,
        numero_cuotas: int,
        mes_inicio_pago: date | None = None,
        monto_por_cuota: Decimal | None = None,
    ) -> Result[InstallmentPurchase, ValidationError | DatabaseError]:
        """Crear una compra en cuotas a partir de un gasto"""

        # Validaciones
        if numero_cuotas < 1 or numero_cuotas > 48:
            return Err(ValidationError("Las cuotas deben ser entre 1 y 48"))

        if expense.monto <= 0:
            return Err(ValidationError("El monto debe ser mayor a 0"))

        # Convertir a Decimal para precisión exacta
        monto_total = (
            expense.monto if isinstance(expense.monto, Decimal)
            else Decimal(str(expense.monto))
        )

        # Calcular monto por cuota con redondeo contable (ROUND_HALF_UP)
        if monto_por_cuota is not None and monto_por_cuota > 0:
            monto_cuota = Decimal(str(monto_por_cuota)).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
            monto_total = monto_cuota * numero_cuotas
        else:
            # Usar ROUND_DOWN para las primeras N-1 cuotas
            # La última se ajusta con el residuo
            from decimal import ROUND_DOWN
            monto_cuota = (monto_total / numero_cuotas).quantize(
                Decimal("1"), rounding=ROUND_DOWN
            )
            monto_total = monto_cuota * numero_cuotas

        # Actualizar el gasto con el total real si cambió
        if monto_total != expense.monto and self._expense_repo and expense.id:
            expense.monto = monto_total
            self._expense_repo.update(expense)

        # Si no se especifica mes_inicio, usar el mes siguiente
        if mes_inicio_pago is None:
            mes_inicio_pago = _add_months(expense.fecha, 1)
            mes_inicio_pago = mes_inicio_pago.replace(day=1)

        # Calcular fecha de última cuota
        fecha_ultima = _add_months(mes_inicio_pago, numero_cuotas - 1)

        purchase = InstallmentPurchase(
            expense_id=expense.id,
            familia_id=expense.familia_id if hasattr(expense, "familia_id") else 0,
            nombre_tarjeta=nombre_tarjeta,
            monto_total=monto_total,
            numero_cuotas=numero_cuotas,
            cuotas_pagadas=0,
            monto_por_cuota=monto_cuota,
            fecha_compra=expense.fecha,
            mes_inicio_pago=mes_inicio_pago,
            fecha_ultima_cuota=fecha_ultima,
            activo=True,
            completado=False,
            vectorizado=False,
            descripcion=expense.descripcion,
        )

        return self._purchase_repo.add(purchase)

    def pagar_cuota(
        self, purchase_id: int, fecha_pago: date | None = None
    ) -> Result[InstallmentPayment, ValidationError | DatabaseError]:
        """Registrar el pago de una cuota"""

        # Obtener la compra en cuotas
        purchase_result = self._purchase_repo.get_by_id(purchase_id)
        if isinstance(purchase_result, Err):
            return purchase_result

        purchase = purchase_result.ok()

        if purchase.completado:
            return Err(ValidationError("Esta compra ya está completamente pagada"))

        # Calcular número de cuota actual
        numero_cuota = purchase.cuotas_pagadas + 1
        es_ultima = numero_cuota == purchase.numero_cuotas

        # Ajuste de residuo en la última cuota (contabilidad uruguaya)
        if es_ultima:
            monto_pagado = purchase.monto_total - (
                purchase.monto_por_cuota * (purchase.numero_cuotas - 1)
            )
        else:
            monto_pagado = purchase.monto_por_cuota

        if fecha_pago is None:
            fecha_pago = date.today()

        # Registrar el pago
        payment = InstallmentPayment(
            installment_purchase_id=purchase_id,
            familia_id=purchase.familia_id,
            numero_cuota=numero_cuota,
            monto_pagado=monto_pagado,
            fecha_pago=fecha_pago,
        )

        payment_result = self._payment_repo.add(payment)
        if isinstance(payment_result, Err):
            return payment_result

        # Actualizar contador de cuotas
        purchase.cuotas_pagadas = numero_cuota
        if purchase.cuotas_pagadas >= purchase.numero_cuotas:
            purchase.completado = True
            purchase.activo = False

        self._purchase_repo.update(purchase)

        return payment_result

    def get_pending(self) -> list[InstallmentPurchase]:
        """Obtener compras con cuotas pendientes"""
        return list(self._purchase_repo.get_pending())

    def get_payment_history(
        self, purchase_id: int
    ) -> list[InstallmentPayment]:
        """Obtener historial de pagos de una compra"""
        return list(self._payment_repo.get_by_purchase(purchase_id))
