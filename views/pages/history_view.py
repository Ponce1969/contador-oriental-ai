"""
Vista de Historial Familiar — últimos 3 meses de gastos e ingresos.
Diseño uruguayo: claro, directo, sin vueltas.
"""

from __future__ import annotations

from decimal import Decimal

import flet as ft

from controllers.history_controller import HistoryController
from core.session import SessionManager
from core.state import AppState
from constants.responsive import Responsive
from services.infrastructure.formatters import format_pesos
from views.layouts.main_layout import MainLayout


class HistoryView:
    """Vista del historial de los últimos 3 meses."""

    def __init__(self, page: ft.Page, router):
        self.page = page
        self.router = router

        if not SessionManager.is_logged_in(page):
            router.navigate("/login")
            return

        familia_id = SessionManager.get_familia_id(page)
        self.controller = HistoryController(familia_id=familia_id)

    def render(self):
        data = self.controller.get_last_3_months()
        is_mobile = AppState.device == "mobile"
        title_size = 20 if is_mobile else 28

        # ── Título ────────────────────────────────────────────────────────
        content_controls: list[ft.Control] = [
            ft.Text(
                value="📊 Historial Familiar",
                size=title_size,
                weight=ft.FontWeight.BOLD,
            ),
            ft.Text(
                value="Últimos 3 meses de tu hacienda familiar",
                size=13,
                color=ft.Colors.BLUE_GREY_500,
            ),
            ft.Divider(),
        ]

        # ── Tarjetas de mes ────────────────────────────────────────────────
        mes_cards: list[ft.Control] = []
        for m in data.meses:
            var_str = HistoryController.format_variacion(
                data.variacion_gastos if m == data.meses[0] else None
            )
            var_color = HistoryController.variacion_color(
                data.variacion_gastos if m == data.meses[0] else None
            )

            card = ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            value=m.label,
                            size=14 if is_mobile else 16,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_GREY_800,
                        ),
                        ft.Text(
                            value=f"Gastos: {format_pesos(m.total_gastos)}",
                            size=18 if is_mobile else 22,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.DEEP_ORANGE_700,
                        ),
                        ft.Text(
                            value=f"Ingresos: {format_pesos(m.total_ingresos)}",
                            size=12,
                            color=ft.Colors.TEAL_700,
                        ),
                        ft.Text(
                            value=f"Balance: {format_pesos(m.balance)}",
                            size=12,
                            color=ft.Colors.GREEN_700
                            if m.balance >= 0
                            else ft.Colors.RED_700,
                        ),
                        ft.Container(
                            content=ft.Text(
                                value=var_str,
                                size=11,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.WHITE,
                            ),
                            bgcolor=var_color,
                            border_radius=6,
                            padding=ft.padding.symmetric(horizontal=8, vertical=3),
                            alignment=ft.Alignment(0, 0),
                        )
                        if m == data.meses[0] and data.variacion_gastos is not None
                        else ft.Text(
                            value=f"{m.cantidad_gastos} gastos",
                            size=11,
                            color=ft.Colors.BLUE_GREY_400,
                        ),
                    ],
                    spacing=6,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=16 if is_mobile else 20,
                bgcolor=ft.Colors.WHITE,
                border_radius=12,
                border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                shadow=ft.BoxShadow(
                    spread_radius=0,
                    blur_radius=4,
                    color=ft.Colors.BLUE_GREY_100,
                ),
                col=Responsive.COL_THIRD if not is_mobile else Responsive.COL_FULL,
            )
            mes_cards.append(card)

        content_controls.append(
            ft.ResponsiveRow(controls=mes_cards, spacing=12, run_spacing=12)
        )

        # ── Barra comparativa de gastos ───────────────────────────────────
        content_controls.extend(
            [
                ft.Divider(height=24),
                ft.Text(
                    value="💰 Tendencia de Gastos",
                    size=18 if is_mobile else 20,
                    weight=ft.FontWeight.BOLD,
                ),
            ]
        )

        bar_controls: list[ft.Control] = []
        for m in data.meses:
            ancho = float(m.total_gastos / data.max_gasto) if data.max_gasto > 0 else 0
            ancho_barra = max(ancho, 0.03)  # Mínimo visible

            bar_controls.append(
                ft.Column(
                    controls=[
                        ft.Text(
                            value=m.label,
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_GREY_700,
                        ),
                        ft.Row(
                            controls=[
                                ft.Container(
                                    content=ft.Text(
                                        value=format_pesos(m.total_gastos),
                                        size=12,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.WHITE,
                                    ),
                                    bgcolor=ft.Colors.DEEP_ORANGE_400,
                                    border_radius=6,
                                    padding=ft.padding.symmetric(
                                        horizontal=10, vertical=6
                                    ),
                                    width=max(int(ancho_barra * 300), 80),
                                ),
                            ],
                        ),
                    ],
                    spacing=4,
                )
            )

        content_controls.append(
            ft.Container(
                content=ft.Column(controls=bar_controls, spacing=12),
                padding=16 if is_mobile else 20,
                bgcolor=ft.Colors.ORANGE_50,
                border_radius=12,
                border=ft.border.all(1, ft.Colors.ORANGE_200),
            )
        )

        # ── Top Categorías ─────────────────────────────────────────────────
        if data.top_categorias:
            cat_controls: list[ft.Control] = [
                ft.Text(
                    value="📂 Top Categorías (3 meses)",
                    size=18 if is_mobile else 20,
                    weight=ft.FontWeight.BOLD,
                ),
            ]

            max_cat = data.top_categorias[0][1] if data.top_categorias else Decimal("1")
            if max_cat == Decimal("0"):
                max_cat = Decimal("1")

            for nombre_cat, total_cat in data.top_categorias:
                pct = float(total_cat / max_cat) if max_cat > 0 else 0

                cat_controls.append(
                    ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        value=nombre_cat,
                                        size=14,
                                        weight=ft.FontWeight.BOLD,
                                        expand=True,
                                    ),
                                    ft.Text(
                                        value=format_pesos(total_cat),
                                        size=14,
                                        color=ft.Colors.DEEP_ORANGE_700,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                ],
                            ),
                            ft.ProgressBar(
                                value=pct,
                                color=ft.Colors.DEEP_ORANGE_400,
                                bgcolor=ft.Colors.DEEP_ORANGE_100,
                                height=8,
                            ),
                        ],
                        spacing=3,
                    )
                )

            content_controls.append(
                ft.Container(
                    content=ft.Column(controls=cat_controls, spacing=14),
                    padding=16 if is_mobile else 20,
                    bgcolor=ft.Colors.WHITE,
                    border_radius=12,
                    border=ft.border.all(1, ft.Colors.BLUE_GREY_200),
                    shadow=ft.BoxShadow(
                        spread_radius=0,
                        blur_radius=4,
                        color=ft.Colors.BLUE_GREY_100,
                    ),
                )
            )

        # ── Botón "Preguntale al Contador" ────────────────────────────────
        content_controls.extend(
            [
                ft.Divider(height=24),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                value="🧮 ¿Tenés preguntas sobre estos 3 meses?",
                                size=16 if is_mobile else 18,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.BLUE_GREY_800,
                            ),
                            ft.Text(
                                value="Preguntale al Contador Oriental con todo el contexto listo.",
                                size=13,
                                color=ft.Colors.BLUE_GREY_500,
                            ),
                        ],
                        spacing=4,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=16,
                    bgcolor=ft.Colors.INDIGO_50,
                    border_radius=12,
                    border=ft.border.all(1, ft.Colors.INDIGO_200),
                ),
                ft.ElevatedButton(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.PSYCHOLOGY, size=20, color=ft.Colors.WHITE),
                            ft.Text(
                                value="Preguntale al Contador",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.WHITE,
                            ),
                        ],
                        spacing=8,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    on_click=lambda _: self.router.navigate("/ai-contador"),
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.INDIGO_600,
                        color=ft.Colors.WHITE,
                        padding=16,
                        shape=ft.RoundedRectangleBorder(radius=12),
                    ),
                ),
            ]
        )

        content = ft.Column(
            controls=content_controls,
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
        )

        return MainLayout(
            page=self.page,
            content=content,
            router=self.router,
        )