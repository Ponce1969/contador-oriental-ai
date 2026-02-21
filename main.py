import os

import flet as ft

from configs.app_config import AppConfig
from core.error_handler import GlobalErrorHandler
from core.logger import get_logger
from core.responsive import get_device_type
from core.sqlalchemy_session import create_tables
from core.state import AppState

logger = get_logger("App")

def main(page: ft.Page):
    try:
        page.title = "Auditor Familiar"
        page.window.width = 1000
        page.window.height = 700
        page.window.resizable = True
        page.theme_mode = ft.ThemeMode.LIGHT
        page.padding = 0
        page.spacing = 0
        
        # Configurar icono personalizado de la aplicación (formato ICO para Windows)
        page.window_icon = "assets/icon-gastos.ico"  # type: ignore

        # Inicializar base de datos
        create_tables()
        logger.info("Base de datos inicializada")

        # Banner de bienvenida
        def close_welcome_banner(e):
            page.banner.open = False  # type: ignore
            page.update()

        def go_to_family(e):
            page.banner.open = False  # type: ignore
            router.navigate("/family")
            page.update()

        page.banner = ft.Banner(  # type: ignore
            bgcolor=ft.Colors.BLUE_50,
            leading=ft.Icon(icon=ft.Icons.WAVING_HAND, color=ft.Colors.BLUE, size=40),
            content=ft.Row(
                controls=[
                    ft.Icon(icon=ft.Icons.INFO, color=ft.Colors.BLUE_400),
                    ft.Text(
                        value="¡Bienvenido al Auditor Familiar! "
                        "Gestiona tus finanzas de forma fácil."
                    ),
                ],
                spacing=10
            ),
            actions=[
                ft.TextButton(content=ft.Text(value="Ir a Familia"), on_click=go_to_family),
                ft.TextButton(content=ft.Text(value="Cerrar"), on_click=close_welcome_banner),
            ],
        )

        if page.platform in (
            ft.PagePlatform.WINDOWS,
            ft.PagePlatform.LINUX,
            ft.PagePlatform.MACOS
        ):
            page.window.width = AppConfig.DEFAULT_SCREEN["width"]
            page.window.height = AppConfig.DEFAULT_SCREEN["height"]

        from core.i18n import I18n
        I18n.load("pt")

        from core.router import Router
        from core.session import SessionManager

        router = Router(page)

        def on_resize(e: object) -> None:
            new_device = get_device_type(page.width)
            if new_device != AppState.device:
                AppState.device = new_device
                router.navigate(router.current_route)

        page.on_resize = on_resize
        AppState.device = get_device_type(page.width or 1280)

        # Verificar si hay sesión activa
        if SessionManager.is_logged_in(page):
            # Usuario logueado - mostrar banner y dashboard
            page.banner.open = True  # type: ignore
            router.navigate("/")
        else:
            # No hay sesión - ir a login
            router.navigate("/login")

        logger.info("Aplicação iniciada com sucesso")
        
    except Exception as e:
        GlobalErrorHandler.handle(page, e)

# Detectar si estamos en Docker (modo web) o local (modo desktop)
# Si existe POSTGRES_HOST, estamos en Docker
if os.getenv("POSTGRES_HOST"):
    ft.run(
        main,
        assets_dir="assets",
        view=ft.AppView.WEB_BROWSER,
        port=int(os.getenv("APP_PORT", "8550")),
        host="0.0.0.0"
    )
else:
    # Modo desktop para desarrollo local
    ft.run(
        main,
        assets_dir="assets"
    )

