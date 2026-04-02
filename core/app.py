import flet as ft

from core.i18n import I18n
from core.responsive import get_device_type
from core.state import AppState


class FletingApp:
    def __init__(self, page):
        self.page = page
        AppState.device = AppState.initial_device
        self.page.on_resize = self.on_resize
        I18n.load(AppState.language)
        self.page.appbar = self.build_topbar()
        self._register_file_picker()
        from core.router import Router

        self.router = Router(page)
        self.router.navigate("/")

    def _register_file_picker(self):
        """Registrar FilePicker antes del primer navigate().
        page._internals es un dict del dataclass que persiste toda la sesion.
        """
        import logging

        picker = ft.FilePicker()
        self.page.overlay.append(picker)
        self.page._internals["file_picker"] = picker
        logging.getLogger("App").info(
            "[OCR] FilePicker registrado en _internals: id=%s page_id=%s",
            id(picker),
            id(self.page),
        )

    def build_topbar(self):
        menu_items = []

        menu = I18n.translations.get("menu", {})

        for route, label in menu.items():
            menu_items.append(
                ft.TextButton(
                    content=ft.Text(value=label),
                    icon=ft.Icons.CIRCLE,
                    on_click=lambda e, r=f"/{route}": self.router.navigate(r),
                )
            )

        return ft.AppBar(
            title=ft.Text(value=I18n.t("app.name")),
            actions=menu_items,
            center_title=False,
        )

    def on_resize(self, e):
        real_device = get_device_type(self.page.width)

        # Avoid overwriting on the first fake frame
        if not AppState.initialized:
            AppState.initialized = True

        AppState.device = real_device
        self.page.update()
