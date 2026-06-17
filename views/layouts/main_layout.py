import asyncio
import urllib.parse
from dataclasses import dataclass
from typing import Final, Protocol

import flet as ft

from configs.routes import ROUTES
from controllers.exchange_rate_controller import ExchangeRateController
from core.i18n import I18n
from core.session import SessionManager
from core.state import AppState
from repositories.user_repository import UserRepository
from services.infrastructure.formatters import format_cotizacion


@dataclass(frozen=True)
class WhatsAppConfig:
    """Configuración inmutable para contacto WhatsApp."""

    phone_number: str
    default_message: str
    country_code: str = "598"  # Uruguay

    @property
    def formatted_number(self) -> str:
        """Retorna número con código de país sin +."""
        # Remover cualquier + o espacios existentes
        clean = self.phone_number.replace("+", "").replace(" ", "")
        if not clean.startswith(self.country_code):
            clean = f"{self.country_code}{clean}"
        return clean

    def build_url(self, custom_message: str | None = None) -> str:
        """Construye URL de WhatsApp con mensaje codificado."""
        message = custom_message or self.default_message
        encoded_msg = urllib.parse.quote(message, safe="")
        return f"https://wa.me/{self.formatted_number}?text={encoded_msg}"


class PageNavigator(Protocol):
    """Protocolo para navegación de página."""

    def launch_url(self, url: str, web_window_name: str | None = None) -> None: ...
    def open_dialog(self, dialog: ft.AlertDialog) -> None: ...
    def close_dialog(self, dialog: ft.AlertDialog) -> None: ...


class WhatsAppContactHandler:
    """Handler simple y directo para contacto WhatsApp."""

    WHATSAPP_CONFIG: Final[WhatsAppConfig] = WhatsAppConfig(
        phone_number="99171819",
        default_message="Hola, necesito ayuda con Contador Oriental AI",
    )

    def __init__(self, page: ft.Page) -> None:
        self._page: ft.Page = page

    def _show_snackbar(self, message: str, color: str, duration: int = 3000) -> None:
        """Muestra snackbar simple."""
        snackbar = ft.SnackBar(
            content=ft.Text(message, color=ft.Colors.WHITE),
            bgcolor=color,
            duration=duration,
        )
        self._page.snack_bar = snackbar
        self._page.snack_bar.open = True
        self._page.update()

    async def open_whatsapp(self, custom_message: str | None = None) -> None:
        """Abre WhatsApp de forma simple y directa."""
        url = self.WHATSAPP_CONFIG.build_url(custom_message)

        try:
            # Intentar abrir directamente (launch_url es async)
            await self._page.launch_url(url)
            self._show_snackbar("Abriendo WhatsApp...", ft.Colors.GREEN_400)
        except Exception:
            # Si falla, mostrar URL para copiar manualmente
            self._show_snackbar(
                f"Abre manualmente: {url}", ft.Colors.BLUE_400, duration=8000
            )


class MainLayout(ft.Column):
    def __init__(self, page: ft.Page, content: ft.Control, router: object):
        super().__init__(expand=True, spacing=0)
        self._page: ft.Page = page
        self._router = router
        self._content = content
        self._whatsapp_handler = WhatsAppContactHandler(page)

        self._build()

    def _user_needs_email_banner(self) -> bool:
        """Check if current user is logged in but has no email registered."""
        user_id = SessionManager.get_user_id(self._page)
        if not user_id:
            return False
        user_result = UserRepository().get_by_id(user_id)
        if user_result.is_err():
            return False
        email = user_result.ok_value.email
        return not email  # Show banner if email is None or empty

    @property
    def _is_mobile(self) -> bool:
        return AppState.device == "mobile"

    @property
    def _is_desktop(self) -> bool:
        return AppState.device == "desktop"

    def _build(self) -> None:
        self.controls.clear()

        # TOP BAR
        self.controls.append(self._top_bar())

        # EMAIL BANNER — security reminder for users without email
        from core.session import _sessions

        session_id = self._page.session.id
        session_data = _sessions.get(session_id, {})
        if not session_data.get("email_banner_dismissed"):
            banner = self._email_banner()
            if banner is not None:
                self.controls.append(banner)

        # EXCHANGE RATE BADGE
        badge = self._exchange_rate_badge()
        if badge is not None:
            self.controls.append(badge)

        # CONTENT — padding lateral adaptativo
        content_padding = ft.Padding.symmetric(
            horizontal=8 if self._is_mobile else 24,
            vertical=8 if self._is_mobile else 16,
        )
        self.controls.append(
            ft.Container(
                content=self._content,
                expand=True,
                padding=content_padding,
            )
        )

        # BOTTOM BAR — solo en desktop y tablet (en mobile el hamburger menu ya navega)
        if not self._is_mobile:
            self.controls.append(self._bottom_bar())

    # ---------- EXCHANGE RATE BADGE ----------
    def _email_banner(self) -> ft.Control | None:
        """Banner for users without email — security reminder to add email for password recovery."""
        if not self._user_needs_email_banner():
            return None

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.LOCK_OUTLINE, size=18, color=ft.Colors.AMBER_700),
                    ft.Text(
                        "Para tu seguridad: agregá tu email en Configuración "
                        "para poder recuperar tu contraseña si la olvidás.",
                        size=13,
                        color=ft.Colors.AMBER_900,
                        expand=True,
                    ),
                    ft.TextButton(
                        text="Ir a Configuración",
                        on_click=lambda e: self._router.navigate("/settings"),
                        style=ft.ButtonStyle(
                            color=ft.Colors.BLUE_700,
                            textStyle=ft.TextStyle(size=12, weight=ft.FontWeight.W_600),
                        ),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        icon_size=16,
                        on_click=self._dismiss_email_banner,
                        tooltip="Recordarme más tarde",
                    ),
                ],
                spacing=8,
                alignment=ft.MainAxisAlignment.START,
            ),
            bgcolor=ft.Colors.AMBER_50,
            border=ft.border.all(1, ft.Colors.AMBER_200),
            border_radius=6,
            padding=ft.Padding(left=12, right=4, top=6, bottom=6),
            margin=ft.margin.only(left=8, right=8, top=4, bottom=0),
        )

    def _dismiss_email_banner(self, e: ft.ControlEvent) -> None:
        """Hide the email banner for this session."""
        from core.session import _sessions

        session_id = self._page.session.id
        if session_id in _sessions:
            _sessions[session_id]["email_banner_dismissed"] = True
        # Remove banner from controls and refresh
        if len(self.controls) > 1:
            banner = self.controls[1]
            if isinstance(banner, ft.Container) and hasattr(banner, "bgcolor") and banner.bgcolor == ft.Colors.AMBER_50:
                self.controls.pop(1)
        self.update()

    def _exchange_rate_badge(self) -> ft.Control | None:
        """Badge con cotización USD/UYU del día. None si no hay datos.
        Defensivo: si falla cualquier cosa, no rompe la app.
        """
        try:
            from decimal import Decimal

            ctrl = ExchangeRateController()
            rate, is_fresh = ctrl.get_display_rate()
            if rate == Decimal("0"):
                return None

            color = ft.Colors.LIGHT_BLUE_300 if is_fresh else ft.Colors.AMBER_400
            icon = ft.Icons.TRENDING_UP if is_fresh else ft.Icons.WARNING_AMBER
            label = f"1 USD = {format_cotizacion(rate)}"
            tooltip_text = (
                "Cotización actualizada hoy"
                if is_fresh
                else "Última cotización disponible (no es de hoy)"
            )

            return ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(icon, size=14, color=color),
                        ft.Text(
                            label,
                            size=12,
                            color=ft.Colors.with_opacity(0.85, ft.Colors.ON_SURFACE),
                            weight=ft.FontWeight.W_500,
                        ),
                    ],
                    spacing=4,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                padding=ft.Padding.symmetric(horizontal=12, vertical=4),
                bgcolor=ft.Colors.GREY_100,
                border_radius=20,
                alignment=ft.Alignment(0, 0),
                tooltip=tooltip_text,
            )
        except Exception:
            # Si falla la DB, los imports, o cualquier cosa,
            # simplemente no mostramos el badge. La app sigue funcionando.
            return None

    # ---------- TOP BAR ----------
    def _top_bar(self) -> ft.AppBar:
        menu_items: list[ft.Control] = []

        for route in ROUTES:
            if not route.get("show_in_top"):
                continue

            # Closure correcto para capturar path
            def make_navigate(path: str) -> ft.ControlEvent:
                return lambda e: self._router.navigate(path)

            menu_items.append(
                ft.PopupMenuItem(
                    content=ft.Row(
                        controls=[
                            ft.Icon(route["icon"]),
                            ft.Text(
                                I18n.t(str(route["label"]))
                                if "." in str(route["label"])
                                else str(route["label"])
                            ),
                        ],
                        spacing=10,
                    ),
                    on_click=make_navigate(str(route["path"])),
                )
            )

        # Agregar separador y logout
        menu_items.append(ft.Divider())
        menu_items.append(
            ft.PopupMenuItem(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.LOGOUT, color=ft.Colors.RED_400),
                        ft.Text("Cerrar Sesión", color=ft.Colors.RED_400),
                    ],
                    spacing=10,
                ),
                on_click=self._on_logout,
            )
        )

        username = SessionManager.get_username(self._page) or "Usuario"

        return ft.AppBar(
            title=ft.Text(I18n.t("app.name")),
            actions=[
                ft.Text(f"👤 {username}", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                # Botón de contacto WhatsApp mejorado
                ft.IconButton(
                    icon=ft.Icons.MESSAGE,  # Icono más específico
                    tooltip="¿Necesitas ayuda? Escríbenos por WhatsApp",
                    icon_color=ft.Colors.GREEN_500,
                    on_click=self._on_whatsapp_click,
                ),
                ft.PopupMenuButton(
                    icon=ft.Icons.MENU,
                    items=menu_items,
                ),
            ],
        )

    def _on_whatsapp_click(self, e: ft.ControlEvent) -> None:
        """Handler sincrono que ejecuta la función async en background."""
        asyncio.create_task(self._whatsapp_handler.open_whatsapp())

    def _on_logout(self, e: ft.ControlEvent) -> None:
        """Cerrar sesión y redirigir al login."""
        SessionManager.logout(self._page)
        self._router.navigate("/login")

    # ---------- BOTTOM BAR ----------
    def _bottom_bar(self) -> ft.NavigationBar:
        destinations: list[ft.NavigationBarDestination] = []
        paths: list[str] = []

        for route in ROUTES:
            if route.get("show_in_bottom"):
                destinations.append(
                    ft.NavigationBarDestination(
                        icon=route["icon"],
                        label=I18n.t(route["label"]),
                    )
                )
                paths.append(route["path"])

        def on_change(e: ft.ControlEvent) -> None:
            selected_index: int = e.control.selected_index
            self._router.navigate(paths[selected_index])

        current_index = (
            paths.index(AppState.current_route)
            if AppState.current_route in paths
            else 0
        )

        return ft.NavigationBar(
            destinations=destinations,
            selected_index=current_index,
            on_change=on_change,
        )
