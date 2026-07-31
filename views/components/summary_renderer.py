"""
SummaryRenderer: componente reutilizable para renderizar resúmenes
de ingresos o gastos por categoría con barra de progreso.
Elimina la duplicación entre _render_income_summary y _render_expense_summary
en dashboard_view.py.
"""

from __future__ import annotations

from decimal import Decimal

import flet as ft

from utils.formatters import format_currency


class SummaryRenderer:
    """Renderiza un resumen de categorías con barra de progreso."""

    @staticmethod
    def render(
        summary: dict[str, Decimal],
        color: str,
        color_bg: str,
        currency: str = "UYU",
        empty_msg: str = "No hay registros",
    ) -> ft.Column:
        """
        Renderiza un resumen de categorías con barra de progreso.

        Args:
            summary: dict {categoria: monto}
            color: color de la barra y el monto (ej: ft.Colors.GREEN)
            color_bg: color de fondo de la barra (ej: ft.Colors.GREEN_100)
            currency: moneda para formatear montos (UYU o USD)
            empty_msg: mensaje cuando no hay datos
        """
        if not summary:
            return ft.Column(
                controls=[
                    ft.Text(value=empty_msg, italic=True, color=ft.Colors.GREY_600)
                ]
            )

        total = sum(summary.values(), Decimal("0"))
        sorted_items = sorted(summary.items(), key=lambda x: x[1], reverse=True)

        currency_symbol = "USD " if currency.upper() == "USD" else "$"
        controls = []
        for categoria, monto in sorted_items:
            porcentaje = float(monto / total * 100) if total > 0 else 0.0
            monto_fmt = format_currency(monto, currency=currency)

            controls.append(
                ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Text(
                                    value=categoria,
                                    size=14,
                                    weight=ft.FontWeight.BOLD,
                                    expand=True,
                                ),
                                ft.Text(
                                    value=f"{currency_symbol}{monto_fmt}",
                                    size=14,
                                    color=color,
                                ),
                            ]
                        ),
                        ft.ProgressBar(
                            value=porcentaje / 100,
                            color=color,
                            bgcolor=color_bg,
                            height=8,
                        ),
                        ft.Text(
                            value=f"{porcentaje:.1f}%",
                            size=11,
                            color=ft.Colors.GREY_600,
                        ),
                    ],
                    spacing=3,
                )
            )

        return ft.Column(controls=controls, spacing=15)
