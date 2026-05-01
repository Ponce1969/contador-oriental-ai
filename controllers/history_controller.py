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
from services.ai.expense_formatters import agrupar_gastos
from services.infrastructure.formatters import format_pesos

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
    """Resumen de un mes individual."""

    year: int
    month: int
    label: str  # "Abril 2025"
    total_gastos: Decimal
    total_ingresos: Decimal
    balance: Decimal
    gastos_por_categoria: dict[str, Decimal]
    cantidad_gastos: int


@dataclass(frozen=True)
class HistoryData:
    """Datos completos del historial de 3 meses."""

    meses: list[MonthSummary]
    max_gasto: Decimal  # Para normalizar barras
    top_categorias: list[tuple[str, Decimal]]  # (nombre, total)
    variacion_gastos: Decimal | None  # % vs mes anterior, None si no hay


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

            for i in range(3):
                # Mes actual, anterior, ante-anterior
                mes = today.month - i
                anio = today.year
                while mes < 1:
                    mes += 12
                    anio -= 1

                gastos = list(expense_repo.get_by_month(anio, mes))
                ingresos = list(income_repo.get_by_month(anio, mes))

                total_gastos = sum((g.monto for g in gastos), Decimal("0"))
                total_ingresos = sum((i.monto for i in ingresos), Decimal("0"))
                balance = total_ingresos - total_gastos

                # Gastos por categoría — agrupar_gastos ya retorna Decimal
                resumen = agrupar_gastos(gastos) if gastos else {}
                gastos_por_categoria: dict[str, Decimal] = {}
                for categoria, items in resumen.items():
                    cat_total = sum(
                        (d["total"] for d in items.values()), Decimal("0")
                    )
                    gastos_por_categoria[categoria] = cat_total

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

        # Máximo gasto para normalizar barras
        max_gasto = max((m.total_gastos for m in meses), default=Decimal("1"))
        if max_gasto == Decimal("0"):
            max_gasto = Decimal("1")

        # Top categorías (acumulado 3 meses)
        categorias_acum: dict[str, Decimal] = {}
        for m in meses:
            for cat, total in m.gastos_por_categoria.items():
                categorias_acum[cat] = categorias_acum.get(cat, Decimal("0")) + total

        top_categorias = sorted(categorias_acum.items(), key=lambda x: x[1], reverse=True)[:6]

        # Variación gastos mes actual vs anterior
        variacion: Decimal | None = None
        if len(meses) >= 2 and meses[1].total_gastos > 0:
            actual = meses[0].total_gastos
            anterior = meses[1].total_gastos
            variacion = ((actual - anterior) / anterior) * Decimal("100")

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