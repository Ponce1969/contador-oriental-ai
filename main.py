import asyncio
import os

import flet as ft

from configs.app_config import AppConfig
from core.error_handler import GlobalErrorHandler
from core.events import EventType, event_system
from core.logger import get_logger
from core.responsive import get_device_type
from core.sqlalchemy_session import create_tables
from core.state import AppState

logger = get_logger("App")

_SECRET_KEY_DEFAULT = "CAMBIA_ESTO_genera_con_python_secrets_token_hex_32"
_secret = os.getenv("SECRET_KEY", "")
if _secret == _SECRET_KEY_DEFAULT or not _secret:
    raise ValueError(
        "SECRET_KEY no está configurado. "
        "Generá una con: python -c 'import secrets; print(secrets.token_hex(32))'"
    )


def _setup_memory_observer() -> None:
    """
    Suscribir el MemoryEventHandler al sistema de eventos.
    Esto activa la memoria vectorial automática al guardar gastos.
    Se omite silenciosamente si MEMORY_SERVICE_ENABLED=false.
    """
    if not AppConfig.MEMORY_SERVICE_ENABLED:
        logger.info(
            "[MEMORY] Servicio de memoria deshabilitado (MEMORY_SERVICE_ENABLED=false)"
        )
        return

    try:
        from core.sqlalchemy_session import get_db_session
        from repositories.memoria_repository import MemoriaRepository
        from services.ai.embedding_service import EmbeddingService
        from services.ai.ia_memory_service import IAMemoryService
        from services.ai.memory_event_handler import MemoryEventHandler

        embedding_service = EmbeddingService(
            ollama_url=AppConfig.OLLAMA_BASE_URL,
            model=AppConfig.OLLAMA_EMBEDDING_MODEL,
        )

        def _make_handler_for_familia(familia_id: int) -> MemoryEventHandler:
            with get_db_session() as session:
                repo = MemoriaRepository(session, familia_id)
                memory_service = IAMemoryService(repo, embedding_service)
                return MemoryEventHandler(memory_service)

        async def _dispatch_gasto(event):
            with get_db_session() as session:
                repo = MemoriaRepository(session, event.familia_id)
                memory_service = IAMemoryService(repo, embedding_service)
                handler = MemoryEventHandler(memory_service)
                await handler.handle(event)

        event_system.subscribe(EventType.GASTO_CREADO, _dispatch_gasto)
        logger.info("[MEMORY] Observer de gastos suscrito al EventSystem ✅")

    except Exception as e:
        logger.warning("[MEMORY] No se pudo inicializar el observer: %s", str(e))


async def main(page: ft.Page):
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

        # Activar memoria vectorial (Observer Pattern)
        _setup_memory_observer()

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
                spacing=10,
            ),
            actions=[
                ft.TextButton(
                    content=ft.Text(value="Ir a Familia"), on_click=go_to_family
                ),
                ft.TextButton(
                    content=ft.Text(value="Cerrar"), on_click=close_welcome_banner
                ),
            ],
        )

        if page.platform in (
            ft.PagePlatform.WINDOWS,
            ft.PagePlatform.LINUX,
            ft.PagePlatform.MACOS,
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

        async def _keepalive():
            while True:
                await asyncio.sleep(30)
                try:
                    page.update()
                except Exception:
                    break

        if os.getenv("POSTGRES_HOST"):
            page.run_task(_keepalive)

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
        host="0.0.0.0",
    )
else:
    # Modo desktop para desarrollo local
    ft.run(main, assets_dir="assets")
