import flet as ft

from configs.app_config import AppConfig
from core.error_handler import GlobalErrorHandler
from core.logger import get_logger
from core.sqlalchemy_session import create_tables

logger = get_logger("App")

def main(page: ft.Page):
    try:
        # Inicializar base de datos
        create_tables()
        logger.info("Base de datos inicializada")

        page.assets_dir = "assets"

        if page.platform in (ft.PagePlatform.WINDOWS, ft.PagePlatform.LINUX, ft.PagePlatform.MACOS):
            page.window.width = AppConfig.DEFAULT_SCREEN["width"]
            page.window.height = AppConfig.DEFAULT_SCREEN["height"]

        from core.i18n import I18n
        I18n.load("pt")

        from core.router import Router

        router = Router(page)
        router.navigate("/")

        logger.info("Aplicação iniciada com sucesso")
        
    except Exception as e:
        GlobalErrorHandler.handle(page, e)

ft.app(target=main)

