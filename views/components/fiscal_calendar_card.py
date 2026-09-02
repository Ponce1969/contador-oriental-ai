"""
Componente visual reactivo para el Calendario Fiscal y Vencimientos Oficiales.
Paleta pastel suave (TEAL_50 / TEAL_200), tipado estricto y diseño 100% responsivo.
"""

from __future__ import annotations

from datetime import date

import flet as ft

from controllers.labor_controller import LaborController
from services.labor.domain.fiscal_calendar_dtos import (
    AmountStatus,
    FiscalCalendarSummary,
    FiscalDueDateInfo,
)
from utils.formatters import format_currency


class FiscalCalendarCard(ft.Container):
    """Tarjeta interactiva de calendario fiscal y vencimientos oficiales uruguayos."""

    def __init__(
        self,
        labor_controller: LaborController,
        initial_year: int = 2026,
        initial_month: int | None = None,
        initial_digit: int = 0,
    ) -> None:
        super().__init__()
        self.labor_controller = labor_controller

        today = date.today()
        self.current_year = initial_year
        self.current_month = initial_month or today.month
        self.current_digit = initial_digit
        self.selected_entity_filter: str = "TODOS"

        # Estilo pastel suave
        self.bgcolor = ft.Colors.TEAL_50
        self.border = ft.Border.all(1.5, ft.Colors.TEAL_200)
        self.border_radius = 12
        self.padding = 14
        self.shadow = ft.BoxShadow(
            spread_radius=1,
            blur_radius=6,
            color=ft.Colors.BLUE_GREY_100,
            offset=ft.Offset(0, 2),
        )

        # Estado
        self.current_summary: FiscalCalendarSummary | None = None

        # Controles de filtro
        self._meses = [
            (1, "Enero"),
            (2, "Febrero"),
            (3, "Marzo"),
            (4, "Abril"),
            (5, "Mayo"),
            (6, "Junio"),
            (7, "Julio"),
            (8, "Agosto"),
            (9, "Setiembre"),
            (10, "Octubre"),
            (11, "Noviembre"),
            (12, "Diciembre"),
        ]

        self.month_dropdown = ft.Dropdown(
            label="Mes",
            value=str(self.current_month),
            options=[ft.dropdown.Option(str(m[0]), m[1]) for m in self._meses],
            text_size=13,
            content_padding=ft.Padding(10, 10, 10, 10),
            col={"xs": 12, "sm": 4},
        )
        self.month_dropdown.on_select = self._on_filters_changed

        self.year_dropdown = ft.Dropdown(
            label="Año Fiscal",
            value=str(self.current_year),
            options=[
                ft.dropdown.Option("2025", "2025"),
                ft.dropdown.Option("2026", "2026"),
            ],
            text_size=13,
            content_padding=ft.Padding(10, 10, 10, 10),
            col={"xs": 12, "sm": 3},
        )
        self.year_dropdown.on_select = self._on_filters_changed

        self.digit_dropdown = ft.Dropdown(
            label="Último Dígito RUT / Cédula",
            value=str(self.current_digit),
            options=[ft.dropdown.Option(str(i), f"Dígito {i}") for i in range(10)],
            text_size=13,
            content_padding=ft.Padding(10, 10, 10, 10),
            col={"xs": 12, "sm": 5},
        )
        self.digit_dropdown.on_select = self._on_filters_changed

        self.entity_filter = ft.SegmentedButton(
            selected={self.selected_entity_filter},
            allow_multiple_selection=False,
            segments=[
                ft.Segment(value="TODOS", label=ft.Text("Todos", size=11)),
                ft.Segment(value="DGI", label=ft.Text("DGI", size=11)),
                ft.Segment(value="BPS", label=ft.Text("BPS", size=11)),
                ft.Segment(value="CJPPU", label=ft.Text("CJPPU", size=11)),
            ],
            on_change=self._on_entity_filter_changed,
        )

        self.cards_container = ft.Column(spacing=10)
        self.summary_container = ft.Container()

        self._build_ui()
        self._load_and_render_calendar()

    def _build_ui(self) -> None:
        """Construye la estructura de la tarjeta."""
        header = ft.Row(
            controls=[
                ft.Icon(
                    ft.Icons.CALENDAR_MONTH_OUTLINED,
                    color=ft.Colors.TEAL_900,
                    size=24,
                ),
                ft.Column(
                    controls=[
                        ft.Text(
                            "Calendario Fiscal y Vencimientos Oficiales",
                            size=15,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.TEAL_900,
                        ),
                        ft.Text(
                            "Cronograma oficial DGI, BPS y CJPPU por dígito "
                            "con montos proyectados para el hogar",
                            size=11,
                            color=ft.Colors.TEAL_800,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
        )

        body_content = ft.Column(
            controls=[
                ft.ResponsiveRow(
                    controls=[
                        self.month_dropdown,
                        self.year_dropdown,
                        self.digit_dropdown,
                    ],
                    spacing=12,
                    run_spacing=12,
                ),
                ft.Row(
                    controls=[
                        ft.Text(
                            "Filtrar organismo:",
                            size=11,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.BLUE_GREY_800,
                        ),
                        self.entity_filter,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    wrap=True,
                ),
                ft.Divider(height=12, color=ft.Colors.TEAL_200),
                self.summary_container,
                self.cards_container,
            ],
            spacing=12,
        )

        self.content = ft.ExpansionTile(
            title=header,
            subtitle=ft.Text(
                "Fechas límites oficiales de pago para evitar recargos o multas",
                size=11,
                color=ft.Colors.BLUE_GREY_700,
            ),
            expanded=False,
            controls=[
                ft.Container(
                    content=body_content,
                    padding=ft.Padding(4, 10, 4, 10),
                )
            ],
        )

    def _on_filters_changed(self, _e: ft.ControlEvent) -> None:
        """Actualiza el mes/año/dígito seleccionado."""
        try:
            self.current_month = int(self.month_dropdown.value or "1")
            self.current_year = int(self.year_dropdown.value or "2026")
            self.current_digit = int(self.digit_dropdown.value or "0")
        except ValueError:
            pass
        self._load_and_render_calendar()

    def _on_entity_filter_changed(self, e: ft.ControlEvent) -> None:
        """Filtra la lista de obligaciones por organismo."""
        val = list(e.control.selected)[0] if e.control.selected else "TODOS"
        self.selected_entity_filter = val
        self._render_obligations()

    def _load_and_render_calendar(self) -> None:
        """Ejecuta el cálculo determinístico en el controlador."""
        res = self.labor_controller.obtener_calendario_fiscal(
            year=self.current_year,
            month=self.current_month,
            last_digit=self.current_digit,
            reference_date=date.today(),
        )
        if res.is_ok():
            self.current_summary = res.unwrap()
            self._render_obligations()
        else:
            self.cards_container.controls = [
                ft.Text(
                    f"Error: {res.unwrap_err().message}",
                    color=ft.Colors.RED_700,
                    size=12,
                )
            ]
            self._safe_update()

    def _render_obligations(self) -> None:
        """Renderiza las tarjetas de vencimientos y el banner de total."""
        if not self.current_summary:
            return

        s = self.current_summary

        # Filtrar por organismo
        filtered_obs = s.obligations
        if self.selected_entity_filter != "TODOS":
            filtered_obs = [
                ob
                for ob in s.obligations
                if ob.entity.value == self.selected_entity_filter
            ]

        # ── Banner de resumen mensual consolidado ─────────────────────
        mes_nombre = next((m[1] for m in self._meses if m[0] == s.month), str(s.month))
        tot_str = format_currency(s.total_estimated_amount_uyu, "UYU")

        self.summary_container.content = ft.Container(
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.TEAL_300),
            border_radius=8,
            padding=10,
            content=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.PAYMENTS_OUTLINED,
                        color=ft.Colors.TEAL_800,
                        size=22,
                    ),
                    ft.Text(
                        f"Total Estimado a Pagar en {mes_nombre} {s.year}:",
                        size=12,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.BLUE_GREY_900,
                    ),
                    ft.Text(
                        tot_str,
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.TEAL_900,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                wrap=True,
            ),
        )

        if not filtered_obs:
            ent_label = self.selected_entity_filter
            self.cards_container.controls = [
                ft.Container(
                    bgcolor=ft.Colors.WHITE,
                    border=ft.Border.all(1, ft.Colors.BLUE_GREY_200),
                    border_radius=8,
                    padding=16,
                    content=ft.Text(
                        f"No hay vencimientos de {ent_label} "
                        f"en {mes_nombre} {s.year} (dígito {s.rut_last_digit}).",
                        size=12,
                        color=ft.Colors.BLUE_GREY_700,
                        italic=True,
                    ),
                    alignment=ft.Alignment(0, 0),
                )
            ]
            self._safe_update()
            return

        cards = []
        for ob in filtered_obs:
            cards.append(self._build_obligation_card(ob))

        self.cards_container.controls = cards
        self._safe_update()

    def _build_obligation_card(self, ob: FiscalDueDateInfo) -> ft.Control:
        """Construye la tarjeta visual para una obligación puntual."""
        if ob.urgency_level == "VENCIDO":
            badge_bg = ft.Colors.RED_100
            badge_color = ft.Colors.RED_900
            badge_text = f"VENCIDO HACE {-ob.days_remaining} DÍAS"
        elif ob.urgency_level == "HOY":
            badge_bg = ft.Colors.AMBER_200
            badge_color = ft.Colors.AMBER_900
            badge_text = "VENCE HOY"
        elif ob.urgency_level == "URGENTE":
            badge_bg = ft.Colors.AMBER_100
            badge_color = ft.Colors.AMBER_900
            badge_text = f"VENCE EN {ob.days_remaining} DÍAS"
        elif ob.urgency_level == "PROXIMO":
            badge_bg = ft.Colors.TEAL_100
            badge_color = ft.Colors.TEAL_900
            badge_text = f"EN {ob.days_remaining} DÍAS"
        else:
            badge_bg = ft.Colors.BLUE_GREY_100
            badge_color = ft.Colors.BLUE_GREY_800
            badge_text = f"EN {ob.days_remaining} DÍAS"

        badge = ft.Container(
            content=ft.Text(
                badge_text,
                size=10,
                weight=ft.FontWeight.BOLD,
                color=badge_color,
            ),
            bgcolor=badge_bg,
            border_radius=6,
            padding=ft.Padding(6, 2, 6, 2),
        )

        date_formatted = ob.due_date.strftime("%d/%m/%Y")
        amt_str = (
            format_currency(ob.estimated_amount, ob.currency)
            if ob.estimated_amount
            else "A liquidar"
        )
        if ob.amount_status == AmountStatus.EXACT_LEGAL:
            amt_label = "Cuota Exacta"
        elif ob.amount_status == AmountStatus.CALCULATED_ESTIMATE:
            amt_label = "Monto Estimado"
        else:
            amt_label = ""

        amt_header_txt = f"Importe ({amt_label}):" if amt_label else "Importe:"

        return ft.Container(
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.TEAL_200),
            border_radius=8,
            padding=12,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(
                                ob.title,
                                size=12.5,
                                weight=ft.FontWeight.W_600,
                                color=ft.Colors.BLUE_GREY_900,
                                expand=True,
                            ),
                            badge,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Text(
                        f"Período: {ob.target_period_label}",
                        size=11,
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                    ft.Divider(height=1, color=ft.Colors.BLUE_GREY_100),
                    ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Text(
                                        "Fecha Oficial de Vencimiento:",
                                        size=10.5,
                                        color=ft.Colors.BLUE_GREY_600,
                                    ),
                                    ft.Text(
                                        date_formatted,
                                        size=13,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.TEAL_900,
                                    ),
                                ],
                                spacing=1,
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text(
                                        amt_header_txt,
                                        size=10.5,
                                        color=ft.Colors.BLUE_GREY_600,
                                    ),
                                    ft.Text(
                                        amt_str,
                                        size=13,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.BLUE_GREY_900,
                                    ),
                                ],
                                spacing=1,
                                horizontal_alignment=ft.CrossAxisAlignment.END,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Text(
                        f"📜 Fuente: {ob.legal_source} ({ob.source_reference})",
                        size=10,
                        color=ft.Colors.BLUE_GREY_500,
                        italic=True,
                    ),
                ],
                spacing=6,
            ),
        )

    def _safe_update(self) -> None:
        """Actualiza la página de forma segura contra errores de renderizado."""
        try:
            if self.page:
                self.page.update()
        except (RuntimeError, AttributeError):
            pass
