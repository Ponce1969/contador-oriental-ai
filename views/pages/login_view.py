"""
Vista de Login - Autenticación de usuarios
"""
import flet as ft

from controllers.auth_controller import AuthController
from core.session import SessionManager
from models.errors import AppError


class LoginView:
    """Vista de login"""
    
    def __init__(self, page: ft.Page):
        self.page = page
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
            text="Iniciar Sesión",
            icon=ft.Icons.LOGIN,
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
                                    ft.Icons.ACCOUNT_BALANCE_WALLET,
                                    size=80,
                                    color=ft.Colors.BLUE_600
                                ),
                                ft.Text(
                                    "Auditor Familiar",
                                    size=32,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.BLUE_700
                                ),
                                ft.Text(
                                    "Sistema de Gestión de Finanzas",
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
                                    "Iniciar Sesión",
                                    size=24,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.BLUE_700
                                ),
                                ft.Divider(),
                                self.username_input,
                                self.password_input,
                                self.error_text,
                                self.login_button,
                                
                                # Credenciales por defecto (solo para desarrollo)
                                ft.Container(
                                    content=ft.Column(
                                        controls=[
                                            ft.Divider(),
                                            ft.Text(
                                                "Credenciales por defecto:",
                                                size=12,
                                                color=ft.Colors.GREY_600,
                                                italic=True
                                            ),
                                            ft.Text(
                                                "Usuario: admin",
                                                size=12,
                                                color=ft.Colors.GREY_600
                                            ),
                                            ft.Text(
                                                "Contraseña: admin123",
                                                size=12,
                                                color=ft.Colors.GREY_600
                                            ),
                                        ],
                                        spacing=5
                                    ),
                                    margin=ft.margin.only(top=20)
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
            error = result.err_value
            if isinstance(error, AppError):
                self._show_error(error.message)
            else:
                self._show_error("Error al iniciar sesión")
            return
        
        # Login exitoso - redirigir al dashboard
        user = result.ok_value
        SessionManager.login(self.page, user)
        
        # Mostrar mensaje de bienvenida
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(
                f"¡Bienvenido, {user.nombre_completo or user.username}!"
            ),
            bgcolor=ft.Colors.GREEN_400
        )
        self.page.snack_bar.open = True
        
        # Redirigir al dashboard
        from core.router import Router
        router = Router(self.page)
        router.navigate("/")
    
    def _show_error(self, message: str):
        """Mostrar mensaje de error"""
        self.error_text.value = f"❌ {message}"
        self.error_text.visible = True
        self.page.update()
