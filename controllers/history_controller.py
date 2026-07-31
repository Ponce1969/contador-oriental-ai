"""
Controller para Historial Familiar — últimos 3 meses de gastos e ingresos.
Python puro calcula todo, sin IA.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from controllers.base_controller import BaseController
from repositories.expense_repository import ExpenseRepository
from repositories.income_repository import IncomeRepository
from services.domain.income_service import IncomeService

_MESES: dict[int, str] = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


@dataclass(frozen=True)
class MonthSummary:
    """Resumen de un mes individual con totales por moneda."""

    year: int
    month: int
    label: str  # "Abril 2025"
    total_gastos: dict[str, Decimal]
    total_ingresos: dict[str, Decimal]
    balance: dict[str, Decimal]
    gastos_por_categoria: dict[str, dict[str, Decimal]]  # categoría -> moneda -> monto
    cantidad_gastos: int


@dataclass(frozen=True)
class HistoryData:
    """Datos completos del historial de 3 meses."""

    meses: list[MonthSummary]
    max_gasto: (
        Decimal  # Para normalizar barras (máximo absoluto entre todas las monedas)
    )
    top_categorias: list[tuple[str, str, Decimal]]  # (nombre, moneda, total)
    variacion_gastos: Decimal | None  # % vs mes anterior, None si no hay (sobre UYU)


class HistoryController(BaseController):
    """Controller para la vista de Historial Familiar."""

    def get_title(self) -> str:
        return "Historial Familiar"

    def get_last_3_months(self) -> HistoryData:
        """
        Obtiene resumen de los últimos 3 meses (mes actual y 2 anteriores).
        Una sola sesión de DB para los 3 meses — sin IA, sin embeddings.
        """
        today = date.today()
        meses: list[MonthSummary] = []

        # Una sola sesión para los 3 meses
        with self._get_session() as session:
            expense_repo = ExpenseRepository(session, self._familia_id)
            income_repo = IncomeRepository(session, self._familia_id)
            income_service = IncomeService(income_repo)

            for i in range(3):
                # Mes actual, anterior, ante-anterior
                mes = today.month - i
                anio = today.year
                while mes < 1:
                    mes += 12
                    anio -= 1

                gastos = list(expense_repo.get_by_month(anio, mes))
                # Usar IncomeService para incluir ingresos recurrentes
                ingresos = income_service.list_for_month(anio, mes)

                # Totales por moneda — nunca sumar monedas distintas
                total_gastos: dict[str, Decimal] = {}
                for g in gastos:
                    total_gastos[g.currency] = (
                        total_gastos.get(g.currency, Decimal("0")) + g.monto
                    )

                total_ingresos: dict[str, Decimal] = {}
                for i in ingresos:
                    total_ingresos[i.currency] = (
                        total_ingresos.get(i.currency, Decimal("0")) + i.monto
                    )

                all_currencies = set(total_gastos.keys()) | set(total_ingresos.keys())
                balance: dict[str, Decimal] = {}
                for ccy in all_currencies:
                    balance[ccy] = total_ingresos.get(
                        ccy, Decimal("0")
                    ) - total_gastos.get(ccy, Decimal("0"))

                # Gastos por categoría y moneda
                gastos_por_categoria: dict[str, dict[str, Decimal]] = {}
                for g in gastos:
                    cat = g.categoria.value
                    if cat not in gastos_por_categoria:
                        gastos_por_categoria[cat] = {}
                    gastos_por_categoria[cat][g.currency] = (
                        gastos_por_categoria[cat].get(g.currency, Decimal("0"))
                        + g.monto
                    )

                label = f"{_MESES[mes]} {anio}"

                meses.append(
                    MonthSummary(
                        year=anio,
                        month=mes,
                        label=label,
                        total_gastos=total_gastos,
                        total_ingresos=total_ingresos,
                        balance=balance,
                        gastos_por_categoria=gastos_por_categoria,
                        cantidad_gastos=len(gastos),
                    )
                )

        # Máximo gasto para normalizar barras (entre todas las monedas y meses)
        max_gasto = Decimal("1")
        for m in meses:
            for total in m.total_gastos.values():
                if total > max_gasto:
                    max_gasto = total

        # Top categorías (acumulado 3 meses), manteniendo monedas separadas
        categorias_acum: dict[tuple[str, str], Decimal] = {}
        for m in meses:
            for cat, por_moneda in m.gastos_por_categoria.items():
                for ccy, total in por_moneda.items():
                    key = (cat, ccy)
                    categorias_acum[key] = (
                        categorias_acum.get(key, Decimal("0")) + total
                    )

        top_categorias = sorted(
            ((cat, ccy, total) for (cat, ccy), total in categorias_acum.items()),
            key=lambda x: x[2],
            reverse=True,
        )[:6]

        # Variación gastos mes actual vs anterior (en UYU, moneda principal)
        variacion: Decimal | None = None
        if len(meses) >= 2:
            actual_uyu = meses[0].total_gastos.get("UYU", Decimal("0"))
            anterior_uyu = meses[1].total_gastos.get("UYU", Decimal("0"))
            if anterior_uyu > 0:
                variacion = ((actual_uyu - anterior_uyu) / anterior_uyu) * Decimal(
                    "100"
                )

        return HistoryData(
            meses=meses,
            max_gasto=max_gasto,
            top_categorias=top_categorias,
            variacion_gastos=variacion,
        )

    @staticmethod
    def format_variacion(variacion: Decimal | None) -> str:
        """Formatea la variación porcentual con emoji."""
        if variacion is None:
            return "—"
        valor = float(variacion)
        if valor > 5:
            return f"▲ +{valor:.0f}%"
        if valor < -5:
            return f"▼ {valor:.0f}%"
        return f"≈ {valor:+.0f}%"

    @staticmethod
    def variacion_color(variacion: Decimal | None) -> str:
        """Retorna color Flet según variación."""
        if variacion is None:
            return "#9E9E9E"  # Grey
        valor = float(variacion)
        if valor > 5:
            return "#E53935"  # Red — gastó más
        if valor < -5:
            return "#43A047"  # Green — gastó menos
        return "#FB8C00"  # Orange — estable
