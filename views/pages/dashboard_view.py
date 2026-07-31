"""
Vista del Dashboard - Balance de Ingresos vs Gastos
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import flet as ft

from constants.responsive import Responsive
from controllers.expense_controller import ExpenseController
from controllers.exchange_rate_controller import ExchangeRateController
from controllers.history_controller import HistoryController
from controllers.income_controller import IncomeController
from controllers.installment_controller import InstallmentController
from core.session import SessionManager
from core.state import AppState
from services.infrastructure.formatters import format_pesos
from views.components.summary_renderer import SummaryRenderer
from views.layouts.main_layout import MainLayout

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
        self.installment_controller = InstallmentController(familia_id=familia_id)
        self.history_controller = HistoryController(familia_id=familia_id)

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

        # Generar gastos programados de cuotas (si no se hizo ya)
        try:
            self.installment_controller.generar_gastos_programados(year, month)
        except Exception:
            pass  # No bloquear dashboard por error de cuotas

        # Obtener totales por moneda
        ingresos_uyu = self._get_total_ingresos(year, month, "UYU")
        gastos_uyu = self._get_total_gastos(year, month, "UYU")
        balance_uyu = ingresos_uyu - gastos_uyu

        ingresos_usd = self._get_total_ingresos(year, month, "USD")
        gastos_usd = self._get_total_gastos(year, month, "USD")
        balance_usd = ingresos_usd - gastos_usd

        # Cotización y Patrimonio Consolidado
        exchange_ctrl = ExchangeRateController()
        compra, venta, _ = exchange_ctrl.get_display_rate()
        
        patrimonio_total_uyu = balance_uyu
        equivalencia_usd: Decimal | None = None
        
        if compra > 0 and venta > 0:
            if balance_usd < 0:
                equivalencia_usd = balance_usd * venta
                patrimonio_total_uyu += equivalencia_usd
            else:
                equivalencia_usd = balance_usd * compra
                patrimonio_total_uyu += equivalencia_usd

        # Formatear montos
        balance_uyu_fmt = format_pesos(balance_uyu, currency="UYU")
        balance_usd_fmt = format_pesos(balance_usd, currency="USD")

        is_mobile = AppState.device == "mobile"
        title_size = 20 if is_mobile else 28
        
        # Opcional: mostrar super card del patrimonio consolidado (por ahora lo usaremos solo para alertas y equivalencias como pide el plan ligero)

        content = ft.Column(
            controls=[
                ft.Text(
                    value=f"📊 Dashboard - {month_name} {year}",
                    size=title_size,
                    weight=ft.FontWeight.BOLD,
                ),
                self._build_history_hook(year, month),
                ft.Divider(),
                # Tarjetas de Balance por moneda
                ft.ResponsiveRow(
                    controls=[
                        self._build_balance_card(
                            "Balance UYU",
                            balance_uyu,
                            balance_uyu_fmt,
                            ft.Colors.LIGHT_BLUE_50,
                            is_mobile,
                            "UYU",
                            patrimonio_total_uyu=patrimonio_total_uyu,
                            equivalencia=None,
                        ),
                        self._build_balance_card(
                            "Balance USD",
                            balance_usd,
                            balance_usd_fmt,
                            ft.Colors.BLUE_GREY_50,
                            is_mobile,
                            "USD",
                            patrimonio_total_uyu=patrimonio_total_uyu,
                            equivalencia=equivalencia_usd,
                        ),
                    ],
                    spacing=16,
                    run_spacing=16,
                ),
                self._build_cuotas_card(),
                # Tarjetas de Ingresos y Gastos — ResponsiveRow
                ft.ResponsiveRow(
                    controls=[
                        self._build_summary_total_card(
                            title="Ingresos",
                            icon=ft.Icons.ACCOUNT_BALANCE_WALLET,
                            icon_color=ft.Colors.TEAL_600,
                            title_color=ft.Colors.TEAL_900,
                            amount_color=ft.Colors.GREEN_600,
                            bg_color=ft.Colors.CYAN_50,
                            shadow_color=ft.Colors.TEAL_100,
                            uyu_amount=ingresos_uyu,
                            usd_amount=ingresos_usd,
                            is_mobile=is_mobile,
                        ),
                        self._build_summary_total_card(
                            title="Gastos",
                            icon=ft.Icons.MONEY_OFF,
                            icon_color=ft.Colors.ORANGE_600,
                            title_color=ft.Colors.ORANGE_900,
                            amount_color=ft.Colors.DEEP_ORANGE_600,
                            bg_color=ft.Colors.ORANGE_50,
                            shadow_color=ft.Colors.ORANGE_100,
                            uyu_amount=gastos_uyu,
                            usd_amount=gastos_usd,
                            is_mobile=is_mobile,
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
                        self._build_category_summary_card(
                            title="💰 Ingresos por categoría",
                            summary=self.income_controller.get_summary_by_categories(
                                year=year, month=month
                            ),
                            color=ft.Colors.GREEN,
                            color_bg=ft.Colors.GREEN_100,
                            title_color=ft.Colors.TEAL_700,
                            border_color=ft.Colors.TEAL_200,
                            bg_color=ft.Colors.CYAN_50,
                            empty_msg="No hay ingresos registrados",
                        ),
                        self._build_category_summary_card(
                            title="💸 Gastos por categoría",
                            summary=self.expense_controller.get_summary_by_categories(
                                year=year, month=month
                            ),
                            color=ft.Colors.RED,
                            color_bg=ft.Colors.RED_100,
                            title_color=ft.Colors.ORANGE_700,
                            border_color=ft.Colors.ORANGE_200,
                            bg_color=ft.Colors.ORANGE_50,
                            empty_msg="No hay gastos registrados",
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

    def _build_balance_card(
        self,
        title: str,
        balance: Decimal,
        balance_fmt: str,
        bgcolor: str,
        is_mobile: bool,
        currency: str,
        patrimonio_total_uyu: Decimal = Decimal("0"),
        equivalencia: Decimal | None = None,
    ) -> ft.Container:
        """Construir tarjeta de balance para una moneda."""
        color = self._balance_color(balance, patrimonio_total_uyu, currency)
        icon = self._balance_icon(balance, patrimonio_total_uyu, currency)
        msg = self._balance_msg(balance, currency, patrimonio_total_uyu)

        # Si hay equivalencia, la mostramos chiquito al lado o abajo
        equiv_text = None
        if equivalencia is not None:
            equiv_fmt = format_pesos(equivalencia, currency="UYU")
            equiv_text = ft.Text(
                value=f"(≈ {equiv_fmt})",
                size=12 if is_mobile else 14,
                color=ft.Colors.BLUE_GREY_400,
                weight=ft.FontWeight.W_500,
            )

        column_controls = [
            ft.Text(
                value=title,
                size=14 if is_mobile else 16,
                color=ft.Colors.BLUE_GREY_700,
            ),
            ft.Text(
                value=balance_fmt,
                size=28 if is_mobile else 36,
                weight=ft.FontWeight.BOLD,
                color=color,
            ),
        ]
        
        if equiv_text:
            column_controls.append(equiv_text)
            
        column_controls.append(
            ft.Text(
                value=msg,
                size=12 if is_mobile else 14,
                italic=True,
                color=color,
            )
        )

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(
                                icon=icon,
                                color=color,
                                size=36 if is_mobile else 40,
                            ),
                            ft.Column(
                                controls=column_controls,
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
            bgcolor=bgcolor,
            border_radius=15,
            margin=ft.Margin.only(bottom=16),
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=8,
                color=ft.Colors.BLUE_GREY_100,
            ),
            col=Responsive.COL_HALF,
        )

    def _balance_color(self, balance: Decimal, patrimonio_total: Decimal, currency: str) -> str:
        if balance > 0:
            return ft.Colors.GREEN
        if balance < 0:
            if currency == "USD" and patrimonio_total >= 0:
                return ft.Colors.ORANGE_600  # Es negativo pero hay respaldo
            return ft.Colors.RED
        return ft.Colors.ORANGE

    def _balance_icon(self, balance: Decimal, patrimonio_total: Decimal, currency: str) -> str:
        if balance > 0:
            return ft.Icons.TRENDING_UP
        if balance < 0:
            if currency == "USD" and patrimonio_total >= 0:
                return ft.Icons.SWAP_HORIZ  # Refleja conversión
            return ft.Icons.TRENDING_DOWN
        return ft.Icons.TRENDING_FLAT

    def _balance_msg(self, balance: Decimal, currency: str, patrimonio_total: Decimal) -> str:
        if balance > 0:
            return "¡Excelente! Tienes un superávit"
        if balance < 0:
            if currency == "USD" and patrimonio_total >= 0:
                return "Saldo cubierto por cuenta en pesos"
            return f"⚠️ Atención: Gastos superan ingresos en {currency}"
        return "Balance equilibrado"

    def _build_summary_total_card(
        self,
        title: str,
        icon: str,
        icon_color: str,
        title_color: str,
        amount_color: str,
        bg_color: str,
        shadow_color: str,
        uyu_amount: Decimal,
        usd_amount: Decimal,
        is_mobile: bool,
    ) -> ft.Container:
        """Construir tarjeta de totales (Ingresos/Gastos) mostrando UYU y USD."""
        amounts = []
        if uyu_amount > 0 or usd_amount == 0:
            amounts.append(
                ft.Text(
                    value=format_pesos(uyu_amount, currency="UYU"),
                    size=24 if is_mobile else 28,
                    weight=ft.FontWeight.BOLD,
                    color=amount_color,
                )
            )
        if usd_amount > 0:
            amounts.append(
                ft.Text(
                    value=format_pesos(usd_amount, currency="USD"),
                    size=20 if is_mobile else 24,
                    weight=ft.FontWeight.BOLD,
                    color=amount_color,
                )
            )

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(
                                icon=icon,
                                color=icon_color,
                                size=28,
                            ),
                            ft.Text(
                                value=title,
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=title_color,
                            ),
                        ],
                        spacing=10,
                    ),
                    *amounts,
                ],
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.START,
            ),
            padding=16,
            bgcolor=bg_color,
            border_radius=10,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=6,
                color=shadow_color,
            ),
            col=Responsive.COL_HALF,
        )

    def _build_category_summary_card(
        self,
        title: str,
        summary: dict[tuple[str, str], Decimal],
        color: str,
        color_bg: str,
        title_color: str,
        border_color: str,
        bg_color: str,
        empty_msg: str,
    ) -> ft.Container:
        """Construir card de resumen por categoría separado por moneda."""
        by_currency: dict[str, dict[str, Decimal]] = {}
        for (categoria, currency), monto in summary.items():
            by_currency.setdefault(currency, {})[categoria] = monto

        controls: list[ft.Control] = [
            ft.Text(
                value=title,
                size=14,
                weight=ft.FontWeight.BOLD,
                color=title_color,
            ),
            ft.Divider(),
        ]

        if not by_currency:
            controls.append(
                ft.Text(value=empty_msg, italic=True, color=ft.Colors.GREY_600)
            )
        else:
            for currency in sorted(by_currency.keys()):
                controls.append(
                    ft.Text(
                        value="UYU" if currency == "UYU" else "USD",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_GREY_600,
                    )
                )
                controls.append(
                    SummaryRenderer.render(
                        by_currency[currency],
                        color=color,
                        color_bg=color_bg,
                        currency=currency,
                        empty_msg="No hay registros",
                    )
                )
                controls.append(ft.Divider(height=8))

        return ft.Container(
            content=ft.Column(
                controls=controls,
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=14,
            bgcolor=bg_color,
            border=ft.Border.all(2, border_color),
            border_radius=10,
            height=280,
            col=Responsive.COL_HALF,
        )

    def _build_history_hook(self, year: int, month: int) -> ft.Container:
        """Strip con los últimos 3 meses y link al Historial completo."""
        try:
            data = self.history_controller.get_last_3_months()
        except Exception:
            return ft.Container()

        if not data.meses:
            return ft.Container()

        # Armar strip: "Mayo: $890 / USD 100 | ..."
        strip_parts: list[str] = []
        for m in data.meses:
            gastos_uyu = m.total_gastos.get("UYU", Decimal("0"))
            part = f"{m.label}: {format_pesos(gastos_uyu, currency='UYU')}"
            if m.total_gastos.get("USD"):
                part += f" / {format_pesos(m.total_gastos['USD'], currency='USD')}"
            strip_parts.append(part)

        strip_text = "  |  ".join(strip_parts)

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.ASSESSMENT, size=18, color=ft.Colors.INDIGO_600),
                    ft.Text(
                        value=strip_text,
                        size=12 if AppState.device == "mobile" else 13,
                        color=ft.Colors.BLUE_GREY_700,
                        expand=True,
                    ),
                    ft.TextButton(
                        content=ft.Text(
                            value="Ver historial →",
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.INDIGO_600,
                        ),
                        on_click=lambda _: self.router.navigate("/history"),
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=14, vertical=8),
            bgcolor=ft.Colors.INDIGO_50,
            border_radius=10,
            border=ft.Border.all(1, ft.Colors.INDIGO_200),
        )

    def _build_cuotas_card(self) -> ft.Container:
        """Card de awareness: cuotas pendientes del mes."""
        try:
            planes = self.installment_controller.obtener_cuotas_pendientes()
        except Exception:
            planes = []

        if not planes:
            return ft.Container()  # Sin cuotas pendientes, no mostrar

        total_mes: dict[str, Decimal] = {}
        for p in planes:
            total_mes[p.currency] = (
                total_mes.get(p.currency, Decimal("0")) + p.monto_por_cuota
            )

        partes_cuotas = [
            format_pesos(total_mes[ccy], currency=ccy)
            for ccy in sorted(total_mes.keys())
        ]

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.CREDIT_CARD,
                        color=ft.Colors.BLUE_600,
                        size=22,
                    ),
                    ft.Text(
                        f"Cuotas del mes: {' / '.join(partes_cuotas)}",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_700,
                    ),
                    ft.Text(
                        f"({len(planes)} compras pendientes)",
                        size=12,
                        color=ft.Colors.GREY_500,
                    ),
                ],
                spacing=8,
            ),
            padding=12,
            bgcolor=ft.Colors.BLUE_50,
            border_radius=10,
            margin=ft.Margin.only(bottom=12),
            on_click=lambda _: self.router.navigate("/planes"),
        )

    def _get_total_ingresos(self, year: int, month: int, currency: str) -> Decimal:
        """Obtener total de ingresos del mes para una moneda."""
        totals = self.income_controller.get_total_by_month(
            year, month, currency=currency
        )
        return totals.get(currency, Decimal("0"))

    def _get_total_gastos(self, year: int, month: int, currency: str) -> Decimal:
        """Obtener total de gastos del mes para una moneda."""
        totals = self.expense_controller.get_total_by_month(
            year, month, currency=currency
        )
        return totals.get(currency, Decimal("0"))

    def _get_month_name(self, month: int) -> str:
        """Obtener nombre del mes en español"""
        months = {
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
        return months.get(month, "")
