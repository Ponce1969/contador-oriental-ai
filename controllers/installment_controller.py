"""
Controller para gestión de compras en cuotas
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from result import Ok, Result

from controllers.base_controller import BaseController
from core.events import Event, EventType
from models.categories import ExpenseCategory, PaymentMethod
from models.errors import AppError
from models.expense_model import Expense
from models.installment_model import InstallmentPayment, InstallmentPurchase
from repositories.expense_repository import ExpenseRepository
from repositories.installment_repository import (
    InstallmentPaymentRepository,
    InstallmentPurchaseRepository,
)
from services.domain.installment_service import InstallmentService, _add_months

logger = logging.getLogger(__name__)


class InstallmentController(BaseController):
    """Controller para compras en cuotas con tarjeta"""

    def get_title(self) -> str:
        return "Compras en Cuotas"

    def crear_compra_cuotas(
        self,
        expense: Expense,
        nombre_tarjeta: str,
        numero_cuotas: int,
        mes_inicio_pago: date | None = None,
        monto_por_cuota: Decimal | None = None,
    ) -> Result[InstallmentPurchase, AppError]:
        """Crear una compra en cuotas a partir de un gasto"""
        with self._get_session() as session:
            purchase_repo = InstallmentPurchaseRepository(
                session, self._familia_id
            )
            payment_repo = InstallmentPaymentRepository(session, self._familia_id)
            expense_repo = ExpenseRepository(session, self._familia_id)
            service = InstallmentService(purchase_repo, payment_repo, expense_repo)
            result = service.create_installment(
                expense, nombre_tarjeta, numero_cuotas,
                mes_inicio_pago, monto_por_cuota,
            )

        if isinstance(result, Ok):
            purchase = result.ok()
            event = Event(
                type=EventType.COMPRA_CUOTAS_CREADA,
                familia_id=self._familia_id or 0,
                source_id=purchase.id or 0,
                data={
                    "descripcion": purchase.descripcion,
                    "monto_total": purchase.monto_total,
                    "monto_por_cuota": purchase.monto_por_cuota,
                    "numero_cuotas": purchase.numero_cuotas,
                    "cuotas_restantes": purchase.cuotas_restantes,
                    "tarjeta": purchase.nombre_tarjeta,
                    "is_installment": True,
                },
            )
            self._event_system.fire_and_forget(event)

        return result

    def pagar_cuota(
        self, purchase_id: int, fecha_pago: date | None = None
    ) -> Result[InstallmentPayment, AppError]:
        """Pagar una cuota de una compra"""
        with self._get_session() as session:
            purchase_repo = InstallmentPurchaseRepository(
                session, self._familia_id
            )
            payment_repo = InstallmentPaymentRepository(session, self._familia_id)
            service = InstallmentService(purchase_repo, payment_repo)
            return service.pagar_cuota(purchase_id, fecha_pago)

    def obtener_cuotas_pendientes(self) -> list[InstallmentPurchase]:
        """Obtener lista de compras con cuotas pendientes"""
        with self._get_session() as session:
            repo = InstallmentPurchaseRepository(session, self._familia_id)
            service = InstallmentService(repo, InstallmentPaymentRepository(session))
            return service.get_pending()

    def obtener_historial(
        self, purchase_id: int
    ) -> list[InstallmentPayment]:
        """Obtener todos los pagos de una compra"""
        with self._get_session() as session:
            repo = InstallmentPaymentRepository(session, self._familia_id)
            service = InstallmentService(
                InstallmentPurchaseRepository(session), repo
            )
            return service.get_payment_history(purchase_id)

    def generar_gastos_programados(
        self, anio: int, mes: int
    ) -> int:
        """
        Generar gastos pendientes para cuotas del mes actual.
        Retorna cantidad de gastos creados.
        """
        creados = 0
        planes = self.obtener_cuotas_pendientes()

        for plan in planes:
            if not plan.activo or plan.completado:
                continue

            # Calcular que cuota toca este mes
            cuota_actual = plan.cuotas_pagadas + 1
            fecha_cuota = _add_months(
                plan.mes_inicio_pago or plan.fecha_compra,
                cuota_actual - 1,
            )

            if fecha_cuota.year != anio or fecha_cuota.month != mes:
                continue

            # Verificar si ya existe un gasto para esta cuota
            with self._get_session() as session:
                expense_repo = ExpenseRepository(session, self._familia_id)
                existentes = [
                    e for e in expense_repo.get_by_month(anio, mes)
                    if e.installment_purchase_id == plan.id
                    and f"Cuota {cuota_actual}/{plan.numero_cuotas}" in e.descripcion
                ]
                if existentes:
                    continue  # Ya generado

                # Monto: usar residuo si es la ultima cuota
                es_ultima = cuota_actual == plan.numero_cuotas
                if es_ultima:
                    monto_cuota = plan.monto_total - (
                        plan.monto_por_cuota * (plan.numero_cuotas - 1)
                    )
                else:
                    monto_cuota = plan.monto_por_cuota

                # Crear gasto pendiente
                gasto = Expense(
                    monto=monto_cuota,
                    fecha=fecha_cuota,
                    descripcion=(
                        f"{plan.descripcion} "
                        f"(Cuota {cuota_actual}/{plan.numero_cuotas})"
                    ),
                    categoria=ExpenseCategory.OTROS,
                    metodo_pago=PaymentMethod.TARJETA_CREDITO,
                    es_recurrente=False,
                    frecuencia=None,
                    notas=None,
                    installment_purchase_id=plan.id,
                    pendiente=True,
                )

                result = expense_repo.add(gasto)
                if isinstance(result, Ok):
                    creados += 1

        logger.info(
            "Gastos programados generados: %d para %d/%d",
            creados, mes, anio,
        )
        return creados

    def proyectar_meses(self, meses: int = 6) -> dict[str, Decimal]:
        """Proyectar pagos de cuotas para N meses futuros."""
        proyeccion: dict[str, Decimal] = {}
        planes = self.obtener_cuotas_pendientes()

        for plan in planes:
            cuota_actual = plan.cuotas_pagadas + 1
            for i in range(plan.cuotas_restantes):
                fecha = _add_months(
                    plan.mes_inicio_pago or plan.fecha_compra,
                    cuota_actual - 1 + i,
                )
                if i >= meses:
                    break
                key = f"{fecha.year}-{fecha.month:02d}"
                proyeccion[key] = proyeccion.get(key, Decimal("0")) + plan.monto_por_cuota

        return dict(sorted(proyeccion.items()))
