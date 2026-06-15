import flet as ft

from controllers.auth_controller import AuthController
from controllers.settings_controller import SettingsController
from core.i18n import I18n
from core.state import AppState
from repositories.user_repository import UserRepository
from views.layouts.main_layout import MainLayout


class SettingsView:
    def __init__(self, page, router):
        self.page = page
        self.router = router
        self.controller = SettingsController()
        self.auth_controller = AuthController(page)

        # Load current user's email
        self._current_email = ""
        user_id = self._get_user_id()
        if user_id:
            user_result = UserRepository().get_by_id(user_id)
            if user_result.is_ok():
                self._current_email = user_result.ok_value.email or ""

        self._email_input = ft.TextField(
            label="Email para recuperación de contraseña",
            hint_text="tu@email.com",
            value=self._current_email,
            width=350,
            keyboard_type=ft.KeyboardType.EMAIL,
            autofocus=False,
        )

        self._email_info = ft.Text(
            value=(
                "Si olvidás tu contraseña, enviamos un link de recuperación "
                "a este email. Sin email registrado, no es posible recuperar "
                "la contraseña automáticamente."
            ),
            size=12,
            color=ft.Colors.GREY_500,
            width=350,
        )

        self._email_status = ft.Text(value="", size=13, visible=False)

        self._save_email_button = ft.ElevatedButton(
            content=ft.Row(
                controls=[
                    ft.Icon(icon=ft.Icons.SAVE),
                    ft.Text(value="Guardar email"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=10,
            ),
            on_click=self._on_save_email,
            width=350,
        )

    def _get_user_id(self) -> int | None:
        from core.session import SessionManager

        return SessionManager.get_user_id(self.page)

    def _change_language(self, lang: str):
        I18n.load(lang)
        self.page.update()

    def _on_save_email(self, e):
        user_id = self._get_user_id()
        if not user_id:
            self._show_email_status("Error: sesión no encontrada", error=True)
            return

        email_value = self._email_input.value.strip() or None
        result = self.auth_controller.update_email(user_id, email_value)

        if result.is_ok():
            self._current_email = email_value or ""
            self._show_email_status(result.ok_value, error=False)
        else:
            self._show_email_status(result.err_value.message, error=True)

    def _show_email_status(self, message: str, error: bool = False):
        self._email_status.value = f"{'❌' if error else '✅'} {message}"
        self._email_status.color = ft.Colors.RED_400 if error else ft.Colors.GREEN_400
        self._email_status.visible = True
        self.page.update()

    def _on_remove_email(self, e):
        self._email_input.value = ""
        self._on_save_email(e)

    def render(self):
        content = ft.Column(
            spacing=24,
            controls=[
                # ── Language section ──
                ft.Text(
                    self.controller.get_title(),
                    size=28,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Text(
                    I18n.t("settings.language"),
                    size=16,
                    color=ft.Colors.GREY_600,
                ),
                ft.RadioGroup(
                    value=AppState.language,
                    on_change=lambda e: self._change_language(e.control.value),
                    content=ft.Column(
                        controls=[
                            ft.Radio(value="pt", label="Português 🇧🇷"),
                            ft.Radio(value="en", label="English 🇺🇸"),
                            ft.Radio(value="es", label="Español 🇪🇸"),
                        ]
                    ),
                ),
                # ── Divider ──
                ft.Divider(),
                # ── Email section ──
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Icon(
                                        icon=ft.Icons.MAIL_LOCK,
                                        size=28,
                                        color=ft.Colors.BLUE_600,
                                    ),
                                    ft.Text(
                                        value="Email de recuperación",
                                        size=20,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.BLUE_700,
                                    ),
                                ],
                                spacing=10,
                            ),
                            self._email_info,
                            self._email_input,
                            self._email_status,
                            ft.Row(
                                controls=[
                                    self._save_email_button,
                                    ft.OutlinedButton(
                                        content=ft.Text("Eliminar email"),
                                        on_click=self._on_remove_email,
                                        visible=bool(self._current_email),
                                    ),
                                ],
                                spacing=10,
                            ),
                        ],
                        spacing=12,
                    ),
                    padding=ft.margin.only(top=8),
                ),
            ],
        )

        return MainLayout(
            page=self.page,
            content=content,
            router=self.router,
        )
