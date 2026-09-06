"""
Selector de entorno (Hogar / Campo) para el AppBar.
"""

from __future__ import annotations

import flet as ft

from core.session import SessionManager


class EntornoSwitcher(ft.Container):
    """
    Control compacto para alternar entre el contexto Hogar y Campo.
    Solo es visible si el módulo de Campo está habilitado en Settings.
    """

    def __init__(self, page: ft.Page, router) -> None:
        self._page = page
        self._router = router
        super().__init__()
        self._build_ui()

    def _build_ui(self) -> None:
        if not SessionManager.is_campo_enabled(self._page):
            self.content = None
            self.visible = False
            return

        self.visible = True
        active = SessionManager.get_active_entorno(self._page)
        is_campo = active == "campo"

        # Badge interactivo estilizado
        label = "🚜 Campo" if is_campo else "🏠 Hogar"
        bg_color = ft.Colors.GREEN_100 if is_campo else ft.Colors.LIGHT_BLUE_100
        border_color = ft.Colors.GREEN_400 if is_campo else ft.Colors.LIGHT_BLUE_300
        text_color = ft.Colors.GREEN_900 if is_campo else ft.Colors.LIGHT_BLUE_900

        def toggle_entorno(_: ft.ControlEvent) -> None:
            nuevo = "hogar" if is_campo else "campo"
            SessionManager.set_active_entorno(self._page, nuevo)
            self._router.navigate(self._router.current_route)

        self.content = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text(
                        label,
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=text_color,
                    ),
                    ft.Icon(ft.Icons.SWAP_HORIZ, size=14, color=text_color),
                ],
                spacing=4,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            bgcolor=bg_color,
            border=ft.Border.all(1, border_color),
            border_radius=16,
            padding=ft.Padding.symmetric(horizontal=10, vertical=4),
            ink=True,
            on_click=toggle_entorno,
            tooltip="Tocar para cambiar entre Hogar y Campo",
        )
