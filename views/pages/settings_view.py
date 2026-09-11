import flet as ft

from controllers.auth_controller import AuthController
from controllers.settings_controller import SettingsController
from core.i18n import I18n
from core.session import SessionManager
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
                self._current_email = user_result.unwrap().email or ""

        self._email_input = ft.TextField(
            label="Email para recuperación de contraseña",
            hint_text="tu@email.com",
            value=self._current_email,
            width=350,
            keyboard_type=ft.KeyboardType.EMAIL,
            autofocus=False,
        )

        self._email_info = ft.Text(
            "Guardá tu email para poder restablecer la contraseña si la olvidás.",
            size=12,
            color=ft.Colors.GREY_600,
        )

        self._email_status = ft.Text(value="", visible=False, size=13)

        self._save_email_btn = ft.ElevatedButton(
            "Guardar Email",
            icon=ft.Icons.SAVE_OUTLINED,
            on_click=self._on_save_email,
        )

        is_campo = SessionManager.is_campo_enabled(page)
        self._campo_radio_group = ft.RadioGroup(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Radio(value="hogar"),
                                ft.Column(
                                    controls=[
                                        ft.Text(
                                            "🏠 Solo Hogar / Ciudad",
                                            weight=ft.FontWeight.BOLD,
                                            size=14,
                                            color=ft.Colors.BLUE_900,
                                        ),
                                        ft.Text(
                                            "Finanzas familiares urbanas estándar. "
                                            "Oculta herramientas y rubros de campo.",
                                            size=12,
                                            color=ft.Colors.GREY_700,
                                        ),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.START,
                            vertical_alignment=ft.CrossAxisAlignment.START,
                        ),
                        padding=12,
                        border_radius=8,
                        bgcolor=ft.Colors.BLUE_50,
                        border=ft.Border.all(1, ft.Colors.BLUE_200),
                    ),
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Radio(value="campo"),
                                ft.Column(
                                    controls=[
                                        ft.Text(
                                            "🚜 Hogar + Campo / Actividad Rural",
                                            weight=ft.FontWeight.BOLD,
                                            size=14,
                                            color=ft.Colors.GREEN_900,
                                        ),
                                        ft.Text(
                                            "Habilita el selector de entorno "
                                            "(Hogar / Campo) en la barra superior, "
                                            "insumos rurales y gestión agropecuaria.",
                                            size=12,
                                            color=ft.Colors.GREY_700,
                                        ),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.START,
                            vertical_alignment=ft.CrossAxisAlignment.START,
                        ),
                        padding=12,
                        border_radius=8,
                        bgcolor=ft.Colors.GREEN_50,
                        border=ft.Border.all(1, ft.Colors.GREEN_300),
                    ),
                ],
                spacing=10,
            ),
            value="campo" if is_campo else "hogar",
            on_change=self._on_toggle_campo,
        )
        self._campo_status = ft.Text(value="", visible=False, size=13)

    def _on_toggle_campo(self, e: ft.ControlEvent) -> None:
        enabled = self._campo_radio_group.value == "campo"
        SessionManager.set_campo_enabled(self.page, enabled)

        familia_id = SessionManager.get_familia_id(self.page)
        if familia_id:
            from core.events import Event, EventSystem, EventType
            from repositories.family_repository import FamilyRepository

            FamilyRepository().set_campo_enabled(familia_id, enabled)

            event = Event(
                type=EventType.CAMPO_CONFIG_CAMBIADA,
                familia_id=familia_id,
                data={"enabled": enabled},
            )
            EventSystem().fire_and_forget(event)

        msg = (
            "🚜 Actividad rural habilitada"
            if enabled
            else "🏠 Modo solo hogar activado"
        )
        self._campo_status.value = f"✅ {msg} (guardado permanentemente)"
        self._campo_status.color = (
            ft.Colors.GREEN_700 if enabled else ft.Colors.BLUE_700
        )
        self._campo_status.visible = True
        self.page.update()

    def _get_user_id(self) -> int | None:
        return SessionManager.get_user_id(self.page)

    def _change_language(self, lang: str):
        I18n.load(lang)
        self.page.update()

    def _on_save_email(self, e):
        user_id = self._get_user_id()
        if not user_id:
            self._show_email_status("Sesión no válida", error=True)
            return

        email_value = self._email_input.value.strip() or None
        result = self.auth_controller.update_email(user_id, email_value)

        if result.is_ok():
            self._current_email = email_value or ""
            self._show_email_status(result.unwrap(), error=False)
            # Dismiss email banner in session since user now has email
            if email_value:
                from core.session import _sessions

                session_id = self.page.session.id
                if session_id in _sessions:
                    _sessions[session_id]["email_banner_dismissed"] = True
        else:
            self._show_email_status(result.unwrap_err().message, error=True)

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
            scroll=ft.ScrollMode.AUTO,
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
                                    self._save_email_btn,
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
                    padding=ft.Padding.only(top=8),
                ),
                # ── Divider ──
                ft.Divider(),
                # ── Campo / Agro section ──
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Icon(
                                        ft.Icons.AGRICULTURE,
                                        size=28,
                                        color=ft.Colors.GREEN_700,
                                    ),
                                    ft.Text(
                                        value="Actividad Rural / Campo",
                                        size=20,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.GREEN_800,
                                    ),
                                ],
                                spacing=10,
                            ),
                            ft.Text(
                                "Habilita el selector de entorno (Hogar / Campo) "
                                "en la barra superior para gestionar cuentas "
                                "agropecuarias con categorías e insumos rurales.",
                                size=13,
                                color=ft.Colors.GREY_700,
                            ),
                            self._campo_radio_group,
                            self._campo_status,
                        ],
                        spacing=12,
                    ),
                    padding=ft.Padding.only(top=8, bottom=140),
                ),
            ],
        )

        return MainLayout(
            page=self.page,
            content=content,
            router=self.router,
        )
