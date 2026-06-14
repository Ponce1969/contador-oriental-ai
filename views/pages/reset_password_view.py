"""
Vista de reseteo de contraseña — Ingreso de nueva contraseña
"""

import flet as ft

from controllers.auth_controller import AuthController


class ResetPasswordView:
    """Vista para ingresar nueva contraseña usando token"""

    def __init__(self, page: ft.Page, router=None):
        self.page = page
        self.router = router
        self.auth_controller = AuthController(page)
        self.token = None

        self.new_password_input = ft.TextField(
            label="Nueva contraseña",
            hint_text="Mínimo 6 caracteres",
            password=True,
            can_reveal_password=True,
            width=300,
        )

        self.confirm_password_input = ft.TextField(
            label="Confirmar contraseña",
            hint_text="Repetí la nueva contraseña",
            password=True,
            can_reveal_password=True,
            width=300,
            on_submit=self._on_submit,
        )

        self.error_text = ft.Text(value="", color=ft.Colors.RED_400, visible=False)

        self.submit_button = ft.ElevatedButton(
            content=ft.Row(
                controls=[
                    ft.Icon(icon=ft.Icons.SAVE),
                    ft.Text(value="Cambiar contraseña"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=10,
            ),
            on_click=self._on_submit,
            width=300,
        )

    def render(self):
        # Extract token from URL query params
        # Flet stores query params in page.query_params
        # Try multiple ways to get the token since Flet web handling varies
        self.token = None
        
        # Method 1: page.query_params (Flet 0.84+)
        if hasattr(self.page, "query_params") and self.page.query_params:
            self.token = self.page.query_params.get("token")
        
        # Method 2: parse from page.route if it contains query string
        route = getattr(self.page, "route", "")
        if not self.token and route and "?" in route:
            from urllib.parse import parse_qs, urlparse

            parsed = urlparse(route)
            params = parse_qs(parsed.query)
            if "token" in params:
                self.token = params["token"][0]

        # Method 3: parse from the full URL
        url = getattr(self.page, "url", "")
        if not self.token and url:
            from urllib.parse import parse_qs, urlparse

            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            if "token" in params:
                self.token = params["token"][0]

        if not self.token:
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(icon=ft.Icons.ERROR, size=60, color=ft.Colors.RED_400),
                        ft.Text(
                            value="Link inválido",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.RED_400,
                        ),
                        ft.Text(
                            value=(
                                "No se encontró el token de recuperación. "
                                "Solicitá uno nuevo."
                            ),
                            color=ft.Colors.GREY_600,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.TextButton(
                            content=ft.Text("Solicitar nuevo link"),
                            on_click=self._on_forgot_password_click,
                            style=ft.ButtonStyle(color=ft.Colors.BLUE_700),
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=15,
                ),
                expand=True,
                bgcolor=ft.Colors.BLUE_50,
                padding=20,
            )

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Icon(
                                    icon=ft.Icons.LOCK_RESET,
                                    size=60,
                                    color=ft.Colors.BLUE_600,
                                ),
                                ft.Text(
                                    value="Nueva Contraseña",
                                    size=24,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.BLUE_700,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=10,
                        ),
                        margin=ft.Margin.only(bottom=20),
                    ),
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Divider(),
                                self.new_password_input,
                                self.confirm_password_input,
                                self.error_text,
                                self.submit_button,
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=15,
                        ),
                        padding=30,
                        bgcolor=ft.Colors.WHITE,
                        border_radius=10,
                        shadow=ft.BoxShadow(
                            spread_radius=1,
                            blur_radius=10,
                            color=ft.Colors.BLUE_GREY_100,
                            offset=ft.Offset(0, 2),
                        ),
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=20,
            ),
            expand=True,
            bgcolor=ft.Colors.BLUE_50,
            padding=20,
        )

    def _on_submit(self, e):
        # Validate passwords match
        if not self.new_password_input.value or not self.confirm_password_input.value:
            self._show_error("Completá todos los campos")
            return

        if self.new_password_input.value != self.confirm_password_input.value:
            self._show_error("Las contraseñas no coinciden")
            return

        if len(self.new_password_input.value) < 6:
            self._show_error("La contraseña debe tener al menos 6 caracteres")
            return

        # Reset password
        result = self.auth_controller.reset_password(
            self.token, self.new_password_input.value
        )

        if result.is_ok():
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(
                    value=(
                        "¡Contraseña actualizada! "
                        "Iniciá sesión con tu nueva contraseña."
                    )
                ),
                bgcolor=ft.Colors.GREEN_400,
            )
            self.page.snack_bar.open = True
            # Navigate to login
            from core.router import Router

            router = Router(self.page)
            router.navigate("/login")
        else:
            error = result.err()
            self._show_error(
                error.message if error else "Error al cambiar la contraseña"
            )

    def _on_forgot_password_click(self, e):
        from core.router import Router

        router = Router(self.page)
        router.navigate("/forgot-password")

    def _show_error(self, message: str):
        self.error_text.value = f"❌ {message}"
        self.error_text.visible = True
        self.page.update()
