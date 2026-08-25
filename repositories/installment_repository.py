"""
Repository para compras en cuotas
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from database.tables import InstallmentPaymentTable, InstallmentPurchaseTable
from models.installment_model import InstallmentPayment, InstallmentPurchase
from repositories.base_table_repository import BaseTableRepository


class InstallmentPurchaseRepository(
    BaseTableRepository[InstallmentPurchase, InstallmentPurchaseTable]
):
    """Repository para operaciones CRUD de compras en cuotas"""

    def __init__(self, session: Session, familia_id: int | None = None) -> None:
        super().__init__(session, InstallmentPurchaseTable, familia_id)

    def _to_domain(self, table_row: InstallmentPurchaseTable) -> InstallmentPurchase:
        return InstallmentPurchase(
            id=table_row.id,
            expense_id=table_row.expense_id,
            familia_id=table_row.familia_id,
            nombre_tarjeta=table_row.nombre_tarjeta,
            monto_total=table_row.monto_total,
            currency=table_row.currency,
            numero_cuotas=table_row.numero_cuotas,
            cuotas_pagadas=table_row.cuotas_pagadas,
            monto_por_cuota=table_row.monto_por_cuota,
            fecha_compra=table_row.fecha_compra,
            mes_inicio_pago=table_row.mes_inicio_pago,
            fecha_ultima_cuota=table_row.fecha_ultima_cuota,
            activo=table_row.activo,
            completado=table_row.completado,
            vectorizado=table_row.vectorizado,
            descripcion=table_row.descripcion or "",
            created_at=table_row.created_at,
            updated_at=table_row.updated_at,
        )

    def _to_table(self, entity: InstallmentPurchase) -> InstallmentPurchaseTable:
        return InstallmentPurchaseTable(
            expense_id=entity.expense_id,
            familia_id=entity.familia_id,
            nombre_tarjeta=entity.nombre_tarjeta,
            monto_total=entity.monto_total,
            currency=entity.currency,
            numero_cuotas=entity.numero_cuotas,
            cuotas_pagadas=entity.cuotas_pagadas,
            monto_por_cuota=entity.monto_por_cuota,
            fecha_compra=entity.fecha_compra,
            mes_inicio_pago=entity.mes_inicio_pago,
            fecha_ultima_cuota=entity.fecha_ultima_cuota,
            activo=entity.activo,
            completado=entity.completado,
            vectorizado=entity.vectorizado,
            descripcion=entity.descripcion,
        )

    def _update_specific_fields(
        self, table_row: InstallmentPurchaseTable, entity: InstallmentPurchase
    ) -> None:
        table_row.nombre_tarjeta = entity.nombre_tarjeta
        table_row.cuotas_pagadas = entity.cuotas_pagadas
        table_row.activo = entity.activo
        table_row.completado = entity.completado
        table_row.vectorizado = entity.vectorizado

    def get_pending(self) -> Sequence[InstallmentPurchase]:
        """Obtener compras con cuotas pendientes (activas, no completadas)"""
        return [
            self._to_domain(row)
            for row in (
                self.session.query(self.table_model)
                .filter(
                    self.table_model.familia_id == self.familia_id,
                    self.table_model.activo.is_(True),
                    self.table_model.completado.is_(False),
                )
                .all()
            )
        ]

    def get_by_card(self, nombre_tarjeta: str) -> Sequence[InstallmentPurchase]:
        """Obtener compras por nombre de tarjeta"""
        return [
            self._to_domain(row)
            for row in (
                self.session.query(self.table_model)
                .filter(
                    self.table_model.familia_id == self.familia_id,
                    self.table_model.nombre_tarjeta.ilike(f"%{nombre_tarjeta}%"),
                )
                .all()
            )
        ]


class InstallmentPaymentRepository(
    BaseTableRepository[InstallmentPayment, InstallmentPaymentTable]
):
    """Repository para pagos individuales de cuotas"""

    def __init__(self, session: Session, familia_id: int | None = None) -> None:
        super().__init__(session, InstallmentPaymentTable, familia_id)

    def _to_domain(self, table_row: InstallmentPaymentTable) -> InstallmentPayment:
        return InstallmentPayment(
            id=table_row.id,
            installment_purchase_id=table_row.installment_purchase_id,
            expense_id=table_row.expense_id,
            familia_id=table_row.familia_id,
            numero_cuota=table_row.numero_cuota,
            monto_pagado=table_row.monto_pagado,
            fecha_pago=table_row.fecha_pago,
            created_at=table_row.created_at,
        )

    def _to_table(self, entity: InstallmentPayment) -> InstallmentPaymentTable:
        return InstallmentPaymentTable(
            installment_purchase_id=entity.installment_purchase_id,
            expense_id=entity.expense_id,
            familia_id=entity.familia_id,
            numero_cuota=entity.numero_cuota,
            monto_pagado=entity.monto_pagado,
            fecha_pago=entity.fecha_pago,
        )

    def _update_specific_fields(
        self, table_row: InstallmentPaymentTable, entity: InstallmentPayment
    ) -> None:
        pass  # Payments are immutable once created

    def get_by_purchase(self, purchase_id: int) -> Sequence[InstallmentPayment]:
        """Obtener todos los pagos de una compra en cuotas"""
        return [
            self._to_domain(row)
            for row in (
                self.session.query(self.table_model)
                .filter(
                    self.table_model.installment_purchase_id == purchase_id,
                    self.table_model.familia_id == self.familia_id,
                )
                .order_by(self.table_model.numero_cuota)
                .all()
            )
        ]
