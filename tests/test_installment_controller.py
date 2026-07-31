"""
Tests para InstallmentController — foco en herencia de moneda.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from result import Ok

from controllers.expense_controller import ExpenseController
from controllers.installment_controller import InstallmentController
from models.categories import ExpenseCategory, PaymentMethod
from models.expense_model import Expense


class TestInstallmentControllerCurrency:
    """Tests de herencia de moneda desde compra en cuotas a gastos generados."""

    @pytest.fixture
    def controller(self, db_session):
        """Controller de cuotas con familia_id=1."""
        return InstallmentController(session=db_session, familia_id=1)

    @pytest.fixture
    def expense_controller(self, db_session):
        """Controller de gastos con familia_id=1."""
        return ExpenseController(session=db_session, familia_id=1)

    def _create_expense(
        self,
        expense_controller: ExpenseController,
        currency: str,
    ) -> Expense:
        """Helper: crear un gasto de prueba en la moneda indicada."""
        expense = Expense(
            monto=Decimal("12000"),
            currency=currency,
            fecha=date(2026, 5, 15),
            descripcion="Compra en Tienda Inglesa",
            categoria=ExpenseCategory.ALMACEN,
            metodo_pago=PaymentMethod.TARJETA_CREDITO,
        )
        result = expense_controller.add_expense(expense)
        assert isinstance(result, Ok)
        return result.ok()

    def test_generar_gastos_programados_usd_inherits_currency(
        self,
        controller: InstallmentController,
        expense_controller: ExpenseController,
    ):
        """Una compra USD genera gastos USD."""
        expense = self._create_expense(expense_controller, "USD")

        result = controller.crear_compra_cuotas(
            expense=expense,
            nombre_tarjeta="OCA",
            numero_cuotas=4,
            mes_inicio_pago=date(2026, 6, 1),
        )
        assert isinstance(result, Ok)

        creados = controller.generar_gastos_programados(2026, 6)
        assert creados == 1

        gastos_junio = expense_controller.list_expenses_by_month(2026, 6)
        gastos_cuota = [
            g for g in gastos_junio if g.installment_purchase_id == result.ok().id
        ]
        assert len(gastos_cuota) == 1
        assert gastos_cuota[0].currency == "USD"

    def test_generar_gastos_programados_uyu_default(
        self,
        controller: InstallmentController,
        expense_controller: ExpenseController,
    ):
        """Una compra sin moneda explícita genera gastos UYU."""
        expense = self._create_expense(expense_controller, "UYU")

        result = controller.crear_compra_cuotas(
            expense=expense,
            nombre_tarjeta="Santander",
            numero_cuotas=3,
            mes_inicio_pago=date(2026, 7, 1),
        )
        assert isinstance(result, Ok)

        creados = controller.generar_gastos_programados(2026, 7)
        assert creados == 1

        gastos_julio = expense_controller.list_expenses_by_month(2026, 7)
        gastos_cuota = [
            g for g in gastos_julio if g.installment_purchase_id == result.ok().id
        ]
        assert len(gastos_cuota) == 1
        assert gastos_cuota[0].currency == "UYU"
