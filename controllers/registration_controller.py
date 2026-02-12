"""
Controlador para el registro de familias
"""
import flet as ft

from services.registration_service import RegistrationService


class RegistrationController:
    """Controlador para manejar el registro de nuevas familias"""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.service = RegistrationService()
    
    def handle_register(
        self,
        familia_nombre: str,
        familia_email: str,
        admin_username: str,
        admin_password: str,
        admin_nombre_completo: str,
        password_confirm: str,
        error_text: ft.Text,
        success_callback
    ):
        """
        Maneja el proceso de registro
        
        Args:
            familia_nombre: Nombre de la familia
            familia_email: Email de la familia
            admin_username: Username del admin
            admin_password: Contraseña
            admin_nombre_completo: Nombre completo del admin
            password_confirm: Confirmación de contraseña
            error_text: Control de texto para mostrar errores
            success_callback: Función a llamar si el registro es exitoso
        """
        # Limpiar error previo
        error_text.value = ""
        self.page.update()
        
        # Validar que las contraseñas coincidan
        if admin_password != password_confirm:
            error_text.value = "Las contraseñas no coinciden"
            error_text.color = ft.colors.RED_400
            self.page.update()
            return
        
        # Validar campos vacíos
        if not all([familia_nombre, familia_email, admin_username, admin_password, admin_nombre_completo]):
            error_text.value = "Todos los campos son obligatorios"
            error_text.color = ft.colors.RED_400
            self.page.update()
            return
        
        # Intentar registrar
        result = self.service.register_family(
            familia_nombre=familia_nombre.strip(),
            familia_email=familia_email.strip().lower(),
            admin_username=admin_username.strip(),
            admin_password=admin_password,
            admin_nombre_completo=admin_nombre_completo.strip()
        )
        
        if result.is_ok():
            # Registro exitoso
            usuario = result.ok_value
            error_text.value = "¡Registro exitoso! Redirigiendo al login..."
            error_text.color = ft.Colors.GREEN_400
            self.page.update()
            
            # Llamar al callback de éxito (redirigir al login)
            if success_callback:
                success_callback(usuario)
        else:
            # Error en el registro
            error_text.value = result.err_value
            error_text.color = ft.Colors.RED_400
            self.page.update()
