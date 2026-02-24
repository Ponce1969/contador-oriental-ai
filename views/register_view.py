"""
Vista de registro de nuevas familias
"""
import flet as ft

from controllers.registration_controller import RegistrationController


class RegisterView:
    """Vista para registrar una nueva familia"""
    
    def __init__(self, page: ft.Page, router=None):
        self.page = page
        self.router = router
        self.controller = RegistrationController(page)
        
        # Campos del formulario
        self.familia_nombre_field = ft.TextField(
            label="Nombre de la Familia",
            hint_text="Ej: Los García",
            width=400,
            autofocus=True,
            prefix_icon=ft.Icons.PEOPLE
        )
        
        self.familia_email_field = ft.TextField(
            label="Email de la Familia",
            hint_text="familia@ejemplo.com",
            width=400,
            keyboard_type=ft.KeyboardType.EMAIL,
            prefix_icon=ft.Icons.EMAIL
        )
        
        self.admin_username_field = ft.TextField(
            label="Nombre de Usuario (Admin)",
            hint_text="usuario",
            width=400,
            prefix_icon=ft.Icons.PERSON
        )
        
        self.admin_nombre_field = ft.TextField(
            label="Nombre Completo",
            hint_text="Juan García",
            width=400,
            prefix_icon=ft.Icons.BADGE
        )
        
        self.admin_password_field = ft.TextField(
            label="Contraseña",
            hint_text="Mínimo 6 caracteres",
            width=400,
            password=True,
            can_reveal_password=True,
            prefix_icon=ft.Icons.LOCK
        )
        
        self.password_confirm_field = ft.TextField(
            label="Confirmar Contraseña",
            hint_text="Repite la contraseña",
            width=400,
            password=True,
            can_reveal_password=True,
            prefix_icon=ft.Icons.LOCK_OUTLINE
        )
        
        self.error_text = ft.Text(
            value="",
            color=ft.Colors.RED_400,
            size=14,
            text_align=ft.TextAlign.CENTER
        )
    
    def _on_register_click(self, e):
        """Maneja el clic en el botón de registro"""
        def success_callback(usuario):
            """Callback ejecutado después de registro exitoso"""
            import time
            time.sleep(1)
            if self.router:
                self.router.navigate("/login")
        
        self.controller.handle_register(
            familia_nombre=self.familia_nombre_field.value or "",
            familia_email=self.familia_email_field.value or "",
            admin_username=self.admin_username_field.value or "",
            admin_password=self.admin_password_field.value or "",
            admin_nombre_completo=self.admin_nombre_field.value or "",
            password_confirm=self.password_confirm_field.value or "",
            error_text=self.error_text,
            success_callback=success_callback
        )
    
    def _on_login_click(self, e):
        """Navega a la página de login"""
        if self.router:
            self.router.navigate("/login")
    
    def render(self):
        """Renderiza la vista de registro"""
        register_button = ft.ElevatedButton(
            content=ft.Text("Crear Cuenta"),
            width=400,
            height=50,
            on_click=self._on_register_click,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_700,
            )
        )
        
        login_link = ft.TextButton(
            content=ft.Text("¿Ya tienes cuenta? Inicia sesión"),
            on_click=self._on_login_click
        )
        
        # Layout principal
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(height=20),
                    ft.Icon(
                        ft.Icons.PEOPLE,
                        size=80,
                        color=ft.Colors.BLUE_700
                    ),
                    ft.Text(
                        "Registro de Familia",
                        size=32,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER
                    ),
                    ft.Text(
                        "Crea tu cuenta familiar y comienza a gestionar tus gastos",
                        size=16,
                        color=ft.Colors.GREY_700,
                        text_align=ft.TextAlign.CENTER
                    ),
                    ft.Container(height=20),
                    ft.Divider(height=1, color=ft.Colors.GREY_300),
                    ft.Container(height=10),
                    ft.Text(
                        "Datos de la Familia",
                        size=18,
                        weight=ft.FontWeight.BOLD
                    ),
                    self.familia_nombre_field,
                    self.familia_email_field,
                    ft.Container(height=10),
                    ft.Text(
                        "Usuario Administrador",
                        size=18,
                        weight=ft.FontWeight.BOLD
                    ),
                    self.admin_nombre_field,
                    self.admin_username_field,
                    self.admin_password_field,
                    self.password_confirm_field,
                    ft.Container(height=20),
                    self.error_text,
                    register_button,
                    login_link,
                    ft.Container(height=40),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                scroll=ft.ScrollMode.ALWAYS,
                expand=True
            ),
            padding=20,
            expand=True
        )
