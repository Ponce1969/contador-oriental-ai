import flet as ft

from configs.app_config import AppConfig
from core.error_handler import GlobalErrorHandler
from core.logger import get_logger
from core.sqlalchemy_session import create_tables

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
        page.window_icon = "assets/icon-gastos.ico"

        # Inicializar base de datos
        create_tables()
        logger.info("Base de datos inicializada")

        # Banner de bienvenida
        def close_welcome_banner(e):
            page.banner.open = False
            page.update()

        def go_to_family(e):
            page.banner.open = False
            router.navigate("/family")
            page.update()

        page.banner = ft.Banner(
            bgcolor=ft.Colors.BLUE_50,
            leading=ft.Icon(ft.Icons.WAVING_HAND, color=ft.Colors.BLUE, size=40),
            content=ft.Text(
                "¡Bienvenido a tu Auditor Familiar! Comienza registrando a tu familia en Familia para empezar a gestionar tus finanzas.",
                size=14
            ),
            actions=[
                ft.TextButton("Ir a Familia", on_click=go_to_family),
                ft.TextButton("Cerrar", on_click=close_welcome_banner),
            ],
        )

        if page.platform in (ft.PagePlatform.WINDOWS, ft.PagePlatform.LINUX, ft.PagePlatform.MACOS):
            page.window.width = AppConfig.DEFAULT_SCREEN["width"]
            page.window.height = AppConfig.DEFAULT_SCREEN["height"]

        from core.i18n import I18n
        I18n.load("pt")

        from core.router import Router
        router = Router(page)
        
        # Mostrar banner de bienvenida
        page.banner.open = True
        
        router.navigate("/")

        logger.info("Aplicação iniciada com sucesso")
        
    except Exception as e:
        GlobalErrorHandler.handle(page, e)

ft.app(
    target=main,
    assets_dir="assets"
)

