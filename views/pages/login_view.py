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
            width=300,
            autofocus=True
        )
        
        self.password_input = ft.TextField(
            label="Contraseña",
            hint_text="Ingrese su contraseña",
            password=True,
            can_reveal_password=True,
            width=300,
            on_submit=self._on_login
        )
        
        # Mensaje de error
        self.error_text = ft.Text(
            value="",
            color=ft.Colors.RED_400,
            visible=False
        )
        
        # Botón de login
        self.login_button = ft.ElevatedButton(
            content=ft.Row(
                controls=[
                    ft.Icon(icon=ft.Icons.LOGIN),
                    ft.Text(value="Iniciar Sesión")
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=10
            ),
            on_click=self._on_login,
            width=300
        )
    
    def render(self):
        """Renderizar vista de login"""
        return ft.Container(
            content=ft.Column(
                controls=[
                    # Logo/Título
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Icon(
                                    icon=ft.Icons.ACCOUNT_BALANCE_WALLET,
                                    size=80,
                                    color=ft.Colors.BLUE_600
                                ),
                                ft.Text(
                                    value="Auditor Familiar",
                                    size=32,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.BLUE_700
                                ),
                                ft.Text(
                                    value="Sistema de Gestión de Finanzas",
                                    size=16,
                                    color=ft.Colors.GREY_600
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=10
                        ),
                        margin=ft.margin.only(bottom=30)
                    ),
                    
                    # Formulario de login
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text(
                                    value="Iniciar Sesión",
                                    size=24,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.BLUE_700
                                ),
                                ft.Divider(),
                                self.username_input,
                                self.password_input,
                                self.error_text,
                                self.login_button,
                                
                                # Link de registro
                                ft.Container(
                                    content=ft.TextButton(
                                        content=ft.Text("¿No tienes cuenta? Regístrate aquí"),
                                        on_click=self._on_register_click,
                                        style=ft.ButtonStyle(
                                            color=ft.Colors.BLUE_700,
                                        )
                                    ),
                                    margin=ft.margin.only(top=10)
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=15
                        ),
                        padding=30,
                        bgcolor=ft.Colors.WHITE,
                        border_radius=10,
                        shadow=ft.BoxShadow(
                            spread_radius=1,
                            blur_radius=10,
                            color=ft.Colors.BLUE_GREY_100,
                            offset=ft.Offset(0, 2)
                        )
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=20
            ),
            expand=True,
            bgcolor=ft.Colors.BLUE_50,
            padding=20
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
            self.username_input.value,
            self.password_input.value
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
        self.page.snack_bar = ft.SnackBar(  # type: ignore
            content=ft.Text(
                value=f"¡Bienvenido, {user.nombre_completo or user.username}!"
            ),
            bgcolor=ft.Colors.GREEN_400
        )
        self.page.snack_bar.open = True  # type: ignore
        
        # Redirigir al dashboard
        from core.router import Router
        router = Router(self.page)
        router.navigate("/")
    
    def _on_register_click(self, e):
        """Navegar a la página de registro"""
        from core.router import Router
        router = Router(self.page)
        router.navigate("/register")
    
    def _show_error(self, message: str):
        """Mostrar mensaje de error"""
        self.error_text.value = f"❌ {message}"
        self.error_text.visible = True
        self.page.update()
