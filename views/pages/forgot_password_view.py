"""
Vista de recuperación de contraseña — Ingreso de email
"""

import flet as ft

from controllers.auth_controller import AuthController


class ForgotPasswordView:
    """Vista para solicitar recuperación de contraseña"""

    def __init__(self, page: ft.Page, router=None):
        self.page = page
        self.router = router
        self.auth_controller = AuthController(page)

        self.email_input = ft.TextField(
            label="Email",
            hint_text="Ingresá tu email registrado",
            width=300,
            autofocus=True,
        )

        self.message_text = ft.Text(value="", visible=False)

        self.submit_button = ft.ElevatedButton(
            content=ft.Row(
                controls=[
                    ft.Icon(icon=ft.Icons.EMAIL),
                    ft.Text(value="Enviar link de recuperación"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=10,
            ),
            on_click=self._on_submit,
            width=300,
        )

    def render(self):
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
                                    value="Recuperar Contraseña",
                                    size=24,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.BLUE_700,
                                ),
                                ft.Text(
                                    value=(
                                        "Ingresá tu email y te enviaremos un link "
                                        "para crear una nueva contraseña."
                                    ),
                                    size=14,
                                    color=ft.Colors.GREY_600,
                                    text_align=ft.TextAlign.CENTER,
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
                                self.email_input,
                                self.message_text,
                                self.submit_button,
                                ft.Container(
                                    content=ft.TextButton(
                                        content=ft.Text("Volver al login"),
                                        on_click=self._on_login_click,
                                        style=ft.ButtonStyle(
                                            color=ft.Colors.BLUE_700,
                                        ),
                                    ),
                                    margin=ft.Margin.only(top=10),
                                ),
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
        if not self.email_input.value:
            self._show_message("Ingresá tu email", error=True)
            return

        result = self.auth_controller.request_password_reset(self.email_input.value)

        if result.is_ok():
            self._show_message(result.ok_value, error=False)
            # Disable the button to prevent spam
            self.submit_button.disabled = True
            self.page.update()
        else:
            error = result.err()
            self._show_message(
                error.message if error else "Error al procesar la solicitud",
                error=True,
            )

    def _on_login_click(self, e):
        from core.router import Router

        router = Router(self.page)
        router.navigate("/login")

    def _show_message(self, message: str, error: bool = False):
        self.message_text.value = f"{'❌' if error else '✅'} {message}"
        self.message_text.color = ft.Colors.RED_400 if error else ft.Colors.GREEN_400
        self.message_text.visible = True
        self.page.update()
