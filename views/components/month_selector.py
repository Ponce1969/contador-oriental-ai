"""
Selector y navegador temporal de meses para Flet.
Permite alternar de mes con botones anterior/siguiente y volver al mes actual.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

import flet as ft

from core.session import SessionManager

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


class MonthSelector(ft.Container):
    """Componente reutilizable para navegar entre meses."""

    def __init__(
        self,
        page: ft.Page,
        on_change: Callable[[int, int], None],
        year: int | None = None,
        month: int | None = None,
    ) -> None:
        self._page = page
        self._on_change = on_change

        if year is None or month is None:
            self.year, self.month = SessionManager.get_audited_period(page)
        else:
            self.year = year
            self.month = month

        self._label = ft.Text(
            self.formatted_label,
            size=14,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLUE_GREY_900,
        )

        today = date.today()
        self._is_current_month = self.year == today.year and self.month == today.month

        self._btn_today = ft.TextButton(
            content=ft.Text("Hoy", size=12, weight=ft.FontWeight.W_500),
            visible=not self._is_current_month,
            on_click=self._on_click_today,
            style=ft.ButtonStyle(
                padding=ft.Padding.symmetric(horizontal=8, vertical=2)
            ),
        )

        super().__init__(
            content=ft.Row(
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.CHEVRON_LEFT,
                        tooltip="Mes anterior",
                        icon_size=20,
                        on_click=self._on_prev_month,
                    ),
                    self._label,
                    ft.IconButton(
                        icon=ft.Icons.CHEVRON_RIGHT,
                        tooltip="Mes siguiente",
                        icon_size=20,
                        on_click=self._on_next_month,
                    ),
                    self._btn_today,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=20,
            padding=ft.Padding.symmetric(horizontal=10, vertical=2),
        )

    @property
    def formatted_label(self) -> str:
        return f"{_MESES.get(self.month, f'Mes {self.month}')} {self.year}"

    def set_period(self, year: int, month: int, notify: bool = False) -> None:
        """Cambiar período programáticamente."""
        self.year = year
        self.month = month
        SessionManager.set_audited_period(self._page, self.year, self.month)
        self._update_ui()
        if notify:
            self._on_change(self.year, self.month)

    def _update_ui(self) -> None:
        self._label.value = self.formatted_label
        today = date.today()
        self._is_current_month = self.year == today.year and self.month == today.month
        self._btn_today.visible = not self._is_current_month
        self.update()

    def _on_prev_month(self, _: ft.ControlEvent) -> None:
        if self.month == 1:
            self.month = 12
            self.year -= 1
        else:
            self.month -= 1
        SessionManager.set_audited_period(self._page, self.year, self.month)
        self._update_ui()
        self._on_change(self.year, self.month)

    def _on_next_month(self, _: ft.ControlEvent) -> None:
        if self.month == 12:
            self.month = 1
            self.year += 1
        else:
            self.month += 1
        SessionManager.set_audited_period(self._page, self.year, self.month)
        self._update_ui()
        self._on_change(self.year, self.month)

    def _on_click_today(self, _: ft.ControlEvent) -> None:
        today = date.today()
        self.year = today.year
        self.month = today.month
        SessionManager.set_audited_period(self._page, self.year, self.month)
        self._update_ui()
        self._on_change(self.year, self.month)
