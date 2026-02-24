"""
Vista del Dashboard - Balance de Ingresos vs Gastos
"""

from __future__ import annotations

from datetime import date

import flet as ft

from constants.responsive import Responsive
from controllers.expense_controller import ExpenseController
from controllers.income_controller import IncomeController
from core.session import SessionManager
from core.state import AppState
from utils.formatters import format_currency
from views.components.summary_renderer import SummaryRenderer
from views.layouts.main_layout import MainLayout


class DashboardView:
    """Vista del dashboard con balance de ingresos y gastos"""
    
    def __init__(self, page, router):
        self.page = page
        self.router = router
        
        # Verificar login
        if not SessionManager.is_logged_in(page):
            router.navigate("/login")
            return
        
        # Obtener familia_id de la sesión
        familia_id = SessionManager.get_familia_id(page)
        
        # Controllers
        self.income_controller = IncomeController(familia_id=familia_id)
        self.expense_controller = ExpenseController(familia_id=familia_id)
        
        # Contenedores para los datos
        self.balance_card = ft.Container()
        self.income_card = ft.Container()
        self.expense_card = ft.Container()
        self.chart_container = ft.Container()

    def render(self):
        """Renderizar la vista completa"""
        # Obtener mes y año actual
        today = date.today()
        year = today.year
        month = today.month
        month_name = self._get_month_name(month)
        
        # Obtener totales
        total_ingresos = self._get_total_ingresos(year, month)
        total_gastos = self._get_total_gastos(year, month)
        balance = total_ingresos - total_gastos
        
        # Formatear montos
        ingresos_fmt = format_currency(total_ingresos)
        gastos_fmt = format_currency(total_gastos)
        balance_fmt = format_currency(balance)
        
        # Determinar color y mensaje del balance
        if balance > 0:
            balance_color = ft.Colors.GREEN
            balance_icon = ft.Icons.TRENDING_UP
            balance_msg = "¡Excelente! Tienes un superávit"
        elif balance < 0:
            balance_color = ft.Colors.RED
            balance_icon = ft.Icons.TRENDING_DOWN
            balance_msg = "⚠️ Atención: Gastos superan ingresos"
        else:
            balance_color = ft.Colors.ORANGE
            balance_icon = ft.Icons.TRENDING_FLAT
            balance_msg = "Balance equilibrado"
        
        # Calcular porcentajes para barra de progreso
        total = total_ingresos + total_gastos
        if total > 0:
            porcentaje_ingresos = total_ingresos / total
            porcentaje_gastos = total_gastos / total
        else:
            porcentaje_ingresos = 0.5
            porcentaje_gastos = 0.5
        
        is_mobile = AppState.device == "mobile"
        title_size = 20 if is_mobile else 28

        content = ft.Column(
            controls=[
                ft.Text(
                    value=f"📊 Dashboard - {month_name} {year}",
                    size=title_size,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Divider(),

                # Tarjeta de Balance Principal
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Icon(
                                        icon=balance_icon,
                                        color=balance_color,
                                        size=36 if is_mobile else 40,
                                    ),
                                    ft.Column(
                                        controls=[
                                            ft.Text(
                                                value="Balance del mes",
                                                size=14 if is_mobile else 16,
                                                color=ft.Colors.BLUE_GREY_700,
                                            ),
                                            ft.Text(
                                                value=f"${balance_fmt}",
                                                size=28 if is_mobile else 36,
                                                weight=ft.FontWeight.BOLD,
                                                color=balance_color,
                                            ),
                                            ft.Text(
                                                value=balance_msg,
                                                size=12 if is_mobile else 14,
                                                italic=True,
                                                color=balance_color,
                                            ),
                                        ],
                                        spacing=4,
                                        expand=True,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=16,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    padding=20 if is_mobile else 30,
                    bgcolor=ft.Colors.LIGHT_BLUE_50,
                    border_radius=15,
                    margin=ft.margin.only(bottom=16),
                    shadow=ft.BoxShadow(
                        spread_radius=1,
                        blur_radius=8,
                        color=ft.Colors.BLUE_GREY_100,
                    ),
                ),

                # Tarjetas de Ingresos y Gastos — ResponsiveRow
                ft.ResponsiveRow(
                    controls=[
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Row(
                                        controls=[
                                            ft.Icon(
                                                icon=ft.Icons.ACCOUNT_BALANCE_WALLET,
                                                color=ft.Colors.TEAL_600,
                                                size=28,
                                            ),
                                            ft.Text(
                                                value="Ingresos",
                                                size=16,
                                                weight=ft.FontWeight.BOLD,
                                                color=ft.Colors.TEAL_900,
                                            ),
                                        ],
                                        spacing=10,
                                    ),
                                    ft.Text(
                                        value=f"${ingresos_fmt}",
                                        size=24 if is_mobile else 28,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.GREEN_600,
                                    ),
                                    ft.ProgressBar(
                                        value=porcentaje_ingresos,
                                        color=ft.Colors.TEAL_400,
                                        bgcolor=ft.Colors.TEAL_100,
                                        height=10,
                                    ),
                                    ft.Text(
                                        value=(
                                            f"{porcentaje_ingresos * 100:.1f}%"
                                            " del total"
                                        ),
                                        size=12,
                                        color=ft.Colors.TEAL_700,
                                    ),
                                ],
                                spacing=10,
                                horizontal_alignment=ft.CrossAxisAlignment.START,
                            ),
                            padding=16,
                            bgcolor=ft.Colors.CYAN_50,
                            border_radius=10,
                            shadow=ft.BoxShadow(
                                spread_radius=1,
                                blur_radius=6,
                                color=ft.Colors.TEAL_100,
                            ),
                            col=Responsive.COL_HALF,
                        ),
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Row(
                                        controls=[
                                            ft.Icon(
                                                icon=ft.Icons.MONEY_OFF,
                                                color=ft.Colors.ORANGE_600,
                                                size=28,
                                            ),
                                            ft.Text(
                                                value="Gastos",
                                                size=16,
                                                weight=ft.FontWeight.BOLD,
                                                color=ft.Colors.ORANGE_900,
                                            ),
                                        ],
                                        spacing=10,
                                    ),
                                    ft.Text(
                                        value=f"${gastos_fmt}",
                                        size=24 if is_mobile else 28,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.DEEP_ORANGE_600,
                                    ),
                                    ft.ProgressBar(
                                        value=porcentaje_gastos,
                                        color=ft.Colors.ORANGE_400,
                                        bgcolor=ft.Colors.ORANGE_100,
                                        height=10,
                                    ),
                                    ft.Text(
                                        value=(
                                            f"{porcentaje_gastos * 100:.1f}% del total"
                                        ),
                                        size=12,
                                        color=ft.Colors.ORANGE_700,
                                    ),
                                ],
                                spacing=10,
                                horizontal_alignment=ft.CrossAxisAlignment.START,
                            ),
                            padding=16,
                            bgcolor=ft.Colors.ORANGE_50,
                            border_radius=10,
                            shadow=ft.BoxShadow(
                                spread_radius=1,
                                blur_radius=6,
                                color=ft.Colors.ORANGE_100,
                            ),
                            col=Responsive.COL_HALF,
                        ),
                    ],
                    spacing=16,
                    run_spacing=16,
                ),

                ft.Divider(height=24),

                # Resumen por categorías — ResponsiveRow
                ft.Text(
                    value="📈 Resumen detallado",
                    size=18 if is_mobile else 20,
                    weight=ft.FontWeight.BOLD,
                ),

                ft.ResponsiveRow(
                    controls=[
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Text(
                                        value="💰 Ingresos por categoría",
                                        size=14,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.TEAL_700,
                                    ),
                                    ft.Divider(),
                                    SummaryRenderer.render(
                                        self.income_controller.get_summary_by_categories(),
                                        color=ft.Colors.GREEN,
                                        color_bg=ft.Colors.GREEN_100,
                                        empty_msg="No hay ingresos registrados",
                                    ),
                                ],
                                spacing=10,
                                scroll=ft.ScrollMode.AUTO,
                            ),
                            padding=14,
                            bgcolor=ft.Colors.CYAN_50,
                            border=ft.border.all(2, ft.Colors.TEAL_200),
                            border_radius=10,
                            height=280,
                            col=Responsive.COL_HALF,
                        ),
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Text(
                                        value="💸 Gastos por categoría",
                                        size=14,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.ORANGE_700,
                                    ),
                                    ft.Divider(),
                                    SummaryRenderer.render(
                                        self.expense_controller.get_summary_by_categories(),
                                        color=ft.Colors.RED,
                                        color_bg=ft.Colors.RED_100,
                                        empty_msg="No hay gastos registrados",
                                    ),
                                ],
                                spacing=10,
                                scroll=ft.ScrollMode.AUTO,
                            ),
                            padding=14,
                            bgcolor=ft.Colors.ORANGE_50,
                            border=ft.border.all(2, ft.Colors.ORANGE_200),
                            border_radius=10,
                            height=280,
                            col=Responsive.COL_HALF,
                        ),
                    ],
                    spacing=16,
                    run_spacing=16,
                ),
            ],
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
        )
        
        return MainLayout(
            page=self.page,
            content=content,
            router=self.router,
        )

    def _get_total_ingresos(self, year: int, month: int) -> float:
        """Obtener total de ingresos del mes"""
        return self.income_controller.get_total_by_month(year, month)

    def _get_total_gastos(self, year: int, month: int) -> float:
        """Obtener total de gastos del mes"""
        return self.expense_controller.get_total_by_month(year, month)

    def _get_month_name(self, month: int) -> str:
        """Obtener nombre del mes en español"""
        months = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        return months.get(month, "")
