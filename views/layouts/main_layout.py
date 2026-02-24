
import flet as ft

from configs.routes import ROUTES
from core.i18n import I18n
from core.session import SessionManager
from core.state import AppState


class MainLayout(ft.Column):
    def __init__(self, page, content, router):
        super().__init__(expand=True, spacing=0)
        self._page = page
        self.router = router
        self.content = content

        self._build()

    @property
    def _is_mobile(self) -> bool:
        return AppState.device == "mobile"

    @property
    def _is_desktop(self) -> bool:
        return AppState.device == "desktop"

    def _build(self):
        self.controls.clear()

        # TOP BAR
        self.controls.append(self._top_bar())

        # CONTENT — padding lateral adaptativo
        content_padding = ft.padding.symmetric(
            horizontal=8 if self._is_mobile else 24,
            vertical=8 if self._is_mobile else 16,
        )
        self.controls.append(
            ft.Container(
                content=self.content,
                expand=True,
                padding=content_padding,
            )
        )

        # BOTTOM BAR — solo en mobile y tablet
        if not self._is_desktop:
            self.controls.append(self._bottom_bar())

    # ---------- TOP BAR ----------
    def _top_bar(self):
        items = []

        for r in ROUTES:
            if not r.get("show_in_top"):
                continue

            items.append(
                ft.PopupMenuItem(
                    content=ft.Row(
                        controls=[
                            ft.Icon(icon=r["icon"]),  # type: ignore
                            ft.Text(
                                value=I18n.t(r["label"]) if "." in r["label"] else r["label"]  # type: ignore
                            ),
                        ],
                        spacing=10,
                    ),
                    on_click=lambda e, p=r["path"]: self.router.navigate(p),
                )
            )
        
        # Agregar separador y logout
        items.append(ft.Divider())
        items.append(
            ft.PopupMenuItem(
                content=ft.Row(
                    controls=[
                        ft.Icon(icon=ft.Icons.LOGOUT, color=ft.Colors.RED_400),
                        ft.Text(value="Cerrar Sesión", color=ft.Colors.RED_400),
                    ],
                    spacing=10,
                ),
                on_click=self._on_logout,
            )
        )
        
        # Obtener nombre de usuario
        username = SessionManager.get_username(self._page) or "Usuario"

        return ft.AppBar(
            title=ft.Text(value=I18n.t("app.name")),
            actions=[
                ft.Text(
                    value=f"👤 {username}",
                    size=14,
                    color=ft.Colors.ON_SURFACE_VARIANT
                ),
                ft.PopupMenuButton(
                    icon=ft.Icons.MENU,
                    items=items,
                )
            ],
        )
    
    def _on_logout(self, e):
        """Cerrar sesión y redirigir al login"""
        SessionManager.logout(self._page)
        self.router.navigate("/login")

    # ---------- BOTTOM BAR ----------
    def _bottom_bar(self):
        destinations = []
        paths = []

        for r in ROUTES:
            if r.get("show_in_bottom"):
                destinations.append(
                    ft.NavigationBarDestination(
                        icon=r["icon"],
                        label=I18n.t(r["label"]),
                    )
                )
                paths.append(r["path"])

        def on_change(e):
            self.router.navigate(paths[e.control.selected_index])

        return ft.NavigationBar(
            destinations=destinations,
            selected_index=paths.index(AppState.current_route)
            if AppState.current_route in paths else 0,
            on_change=on_change,
        )
