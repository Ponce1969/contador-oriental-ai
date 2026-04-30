"""
Tests para el sistema de compras en cuotas
"""
from __future__ import annotations

from datetime import date

import pytest

from models.expense_model import Expense
from models.installment_model import InstallmentPayment, InstallmentPurchase
from repositories.installment_repository import (
    InstallmentPaymentRepository,
    InstallmentPurchaseRepository,
)
from services.domain.installment_service import InstallmentService


class TestInstallmentService:
    """Tests para el servicio de compras en cuotas"""

    @pytest.fixture
    def service(self, db_session):
        """Fixture: servicio de cuotas con repositorios reales"""
        familia_id = 1
        purchase_repo = InstallmentPurchaseRepository(db_session, familia_id)
        payment_repo = InstallmentPaymentRepository(db_session, familia_id)
        return InstallmentService(purchase_repo, payment_repo)

    @pytest.fixture
    def sample_expense(self):
        """Fixture: gasto de ejemplo para cuotas"""
        return Expense(
            id=None,
            monto=12000.0,
            fecha=date(2026, 5, 15),
            descripcion="Compra en Tienda Inglesa",
            categoria=__import__("models.categories", fromlist=["ExpenseCategory"]).ExpenseCategory.ALMACEN,
            metodo_pago=__import__("models.categories", fromlist=["PaymentMethod"]).PaymentMethod.TARJETA_CREDITO,
            familia_id=1,
        )

    def test_create_installment(self, service, sample_expense):
        """Test: crear compra en 4 cuotas"""
        result = service.create_installment(
            sample_expense,
            nombre_tarjeta="OCA",
            numero_cuotas=4,
        )
        assert result.is_ok()
        purchase = result.ok()
        assert purchase.nombre_tarjeta == "OCA"
        assert purchase.numero_cuotas == 4
        assert purchase.cuotas_pagadas == 0
        assert purchase.monto_por_cuota == 3000.0
        assert purchase.activo is True
        assert purchase.completado is False
        assert purchase.mes_inicio_pago == date(2026, 6, 1)  # Mes siguiente

    def test_create_installment_with_start_month(self, service, sample_expense):
        """Test: crear compra con mes de inicio específico"""
        result = service.create_installment(
            sample_expense,
            nombre_tarjeta="Scotia",
            numero_cuotas=3,
            mes_inicio_pago=date(2026, 7, 1),
        )
        assert result.is_ok()
        purchase = result.ok()
        assert purchase.mes_inicio_pago == date(2026, 7, 1)

    def test_pay_cuota(self, service, sample_expense, db_session):
        """Test: pagar una cuota y actualizar contador"""
        # Crear compra en cuotas
        result = service.create_installment(
            sample_expense,
            nombre_tarjeta="Santander",
            numero_cuotas=3,
        )
        assert result.is_ok()
        purchase = result.ok()

        # Pagar primera cuota
        pay_result = service.pagar_cuota(purchase.id, date(2026, 6, 5))
        assert pay_result.is_ok()

        # Verificar datos del pago
        payment = pay_result.ok()
        assert payment.numero_cuota == 1
        assert payment.monto_pagado == 4000.0  # 12000 / 3

        # Actualizar purchase después del pago
        db_session.commit()

        # Pagar segunda cuota
        pay_result2 = service.pagar_cuota(purchase.id, date(2026, 7, 5))
        assert pay_result2.is_ok()
        payment2 = pay_result2.ok()
        assert payment2.numero_cuota == 2

        # Pagar tercera cuota (última)
        pay_result3 = service.pagar_cuota(purchase.id, date(2026, 8, 5))
        assert pay_result3.is_ok()

        # Verificar historial de pagos
        history = service.get_payment_history(purchase.id)
        assert len(history) == 3

    def test_cannot_pay_completed_installment(self, service, sample_expense):
        """Test: no se puede pagar cuota extra si ya está completo"""
        result = service.create_installment(
            sample_expense,
            nombre_tarjeta="BBVA",
            numero_cuotas=1,
        )
        assert result.is_ok()
        purchase = result.ok()

        # Pagar la única cuota
        service.pagar_cuota(purchase.id)

        # Intentar pagar otra vez - debe fallar
        pay_result = service.pagar_cuota(purchase.id)
        assert pay_result.is_err()

    def test_get_pending(self, service, sample_expense):
        """Test: obtener cuotas pendientes"""
        result = service.create_installment(
            sample_expense,
            nombre_tarjeta="OCA",
            numero_cuotas=4,
        )
        assert result.is_ok()

        pending = service.get_pending()
        assert len(pending) >= 1
        assert pending[0].nombre_tarjeta == "OCA"
        assert pending[0].cuotas_pagadas == 0


class TestHelperFunctions:
    """Tests para funciones auxiliares"""

    def test_add_months_basic(self):
        """Test: agregar meses a fecha"""
        from services.domain.installment_service import _add_months

        result = _add_months(date(2026, 5, 15), 1)
        assert result == date(2026, 6, 15)

        result = _add_months(date(2026, 1, 31), 1)
        assert result == date(2026, 2, 28)  # 31 enero → 28 feb

        result = _add_months(date(2026, 12, 1), 3)
        assert result == date(2027, 3, 1)
