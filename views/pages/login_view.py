"""
Vista de Login - Autenticación de usuarios
"""

import flet as ft

from controllers.auth_controller import AuthController
from core.session import SessionManager
from models.errors import AppError


class LoginView:
    """Vista de login"""

    def __init__(self, page: ft.Page, router=None):
        self.page = page
        self.router = router
        self.auth_controller = AuthController(page)

        # Inputs
        self.username_input = ft.TextField(
            label="Usuario",
            hint_text="Ingrese su nombre de usuario",
            prefix_icon=ft.Icons.PERSON_OUTLINE,
            autofocus=True,
        )

        self.password_input = ft.TextField(
            label="Contraseña",
            hint_text="Ingrese su contraseña",
            password=True,
            can_reveal_password=True,
            prefix_icon=ft.Icons.LOCK_OUTLINE,
            on_submit=self._on_login,
        )

        # Mensaje de error
        self.error_text = ft.Text(value="", color=ft.Colors.RED_400, visible=False)

        # Botón de login
        self.login_button = ft.ElevatedButton(
            content=ft.Text(value="Iniciar Sesión", size=16, weight=ft.FontWeight.BOLD),
            on_click=self._on_login,
            width=float("inf"),
            height=48,
            bgcolor="#1A56DB",
            color=ft.Colors.WHITE,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        )

        # Link de recuperar contraseña
        self.forgot_password_link = ft.TextButton(
            content=ft.Text("¿Olvidaste tu contraseña?"),
            on_click=self._on_forgot_password_click,
            style=ft.ButtonStyle(color=ft.Colors.BLUE_700),
        )

    def render(self):
        """Renderizar vista de login"""
        return ft.Container(
            content=ft.Column(
                controls=[
                    # ── Logo / Cabecera ────────────────────────────────
                    ft.Column(
                        controls=[
                            ft.Icon(
                                icon=ft.Icons.ACCOUNT_BALANCE_WALLET,
                                size=64,
                                color="#1A56DB",
                            ),
                            ft.Text(
                                value="Auditor Familiar",
                                size=24,
                                weight=ft.FontWeight.BOLD,
                                color="#1A56DB",
                            ),
                            ft.Text(
                                value="Sistema de Gestión de Finanzas",
                                size=14,
                                color=ft.Colors.GREY_500,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    # ── Card de Login ──────────────────────────────────
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text(
                                    value="Iniciar Sesión",
                                    size=20,
                                    weight=ft.FontWeight.BOLD,
                                    color="#1A56DB",
                                ),
                                self.username_input,
                                self.password_input,
                                self.error_text,
                                self.login_button,
                                ft.Container(
                                    content=self.forgot_password_link,
                                    alignment=ft.Alignment(0, 0),
                                ),
                                ft.Container(
                                    content=ft.TextButton(
                                        content=ft.Text("¿No tienes cuenta? Regístrate aquí"),
                                        on_click=self._on_register_click,
                                        style=ft.ButtonStyle(color=ft.Colors.BLUE_700),
                                    ),
                                    alignment=ft.Alignment(0, 0),
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=16,
                        ),
                        width=420,
                        padding=ft.Padding(left=32, top=32, right=32, bottom=32),
                        border_radius=16,
                        bgcolor=ft.Colors.WHITE,
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
                spacing=32,
            ),
            expand=True,
            alignment=ft.Alignment(0, 0),
            bgcolor="#F4F6F9",
            padding=20,
        )

    def _on_login(self, e):
        """Manejar intento de login"""
        # Limpiar error previo
        self.error_text.visible = False
        self.page.update()

        # Validar inputs
        if not self.username_input.value or not self.password_input.value:
            self._show_error("Por favor complete todos los campos")
            return

        # Intentar login
        result = self.auth_controller.login(
            self.username_input.value, self.password_input.value
        )

        if result.is_err():
            error = result.err()
            if error is not None and isinstance(error, AppError):
                self._show_error(error.message)
            else:
                self._show_error("Error al iniciar sesión")
            return

        # Login exitoso - redirigir al dashboard
        user = result.ok()
        if user is None:
            self._show_error("Error al iniciar sesión")
            return
        SessionManager.login(self.page, user)

        # Mostrar mensaje de bienvenida
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(
                value=f"¡Bienvenido, {user.nombre_completo or user.username}!"
            ),
            bgcolor=ft.Colors.GREEN_400,
        )
        self.page.snack_bar.open = True

        # Redirigir al dashboard
        from core.router import Router

        router = Router(self.page)
        router.navigate("/")

    def _on_register_click(self, e):
        """Navegar a la página de registro"""
        from core.router import Router

        router = Router(self.page)
        router.navigate("/register")

    def _on_forgot_password_click(self, e):
        """Navegar a la página de recuperar contraseña"""
        from core.router import Router

        router = Router(self.page)
        router.navigate("/forgot-password")

    def _show_error(self, message: str):
        """Mostrar mensaje de error"""
        self.error_text.value = f"❌ {message}"
        self.error_text.visible = True
        self.page.update()
