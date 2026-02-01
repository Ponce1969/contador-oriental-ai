"""
Vista para gestión de miembros de la familia
"""

from __future__ import annotations

import flet as ft
from result import Err, Ok

from controllers.family_member_controller import FamilyMemberController
from core.session import SessionManager
from flet_types.flet_types import CorrectElevatedButton, CorrectSnackBar
from models.errors import AppError
from models.family_member_model import FamilyMember, IncomeType
from views.layouts.main_layout import MainLayout


class FamilyMembersView:
    """Vista para gestionar miembros de la familia"""
    
    def __init__(self, page, router):
        self.page = page
        self.router = router
        
        # Verificar login
        if not SessionManager.is_logged_in(page):
            router.navigate("/login")
            return
        
        # Obtener familia_id de la sesión
        familia_id = SessionManager.get_familia_id(page)
        
        # Controller
        self.controller = FamilyMemberController(familia_id=familia_id)
        
        # Campos del formulario
        self.nombre_input = ft.TextField(
            label="Nombre",
            hint_text="Ej: Juan Pérez",
            width=300
        )
        
        self.sueldo_input = ft.TextField(
            label="Sueldo mensual ($) - Solo para Sueldo fijo o Mixto",
            hint_text="Ej: 50.000 o 50000",
            width=300
        )
        
        self.tipo_ingreso_dropdown = ft.Dropdown(
            label="Tipo de ingreso",
            width=200,
            options=[
                ft.dropdown.Option(key=tipo.name, text=tipo.value)
                for tipo in IncomeType
            ]
        )
        
        self.notas_input = ft.TextField(
            label="Notas (opcional)",
            multiline=True,
            min_lines=2,
            max_lines=3,
            width=600
        )
        
        # Lista de miembros
        self.members_column = ft.Column(spacing=10)
        
        # Estado de edición
        self.editing_member_id = None

    def render(self):
        """Renderizar la vista completa"""
        content = ft.Column(
            controls=[
                ft.Text(value=self.controller.get_title(), size=28, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                
                # Formulario de registro
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                value=(
                                    "👥 Agregar miembro de la familia"
                                    if not self.editing_member_id
                                    else "✏️ Editar miembro de la familia"
                                ),
                                size=20,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.PURPLE_700
                            ),
                            ft.Row(
                                controls=[
                                    self.nombre_input,
                                    self.tipo_ingreso_dropdown,
                                    self.sueldo_input,
                                ],
                                spacing=10
                            ),
                            self.notas_input,
                            ft.Row(
                                controls=[
                                    CorrectElevatedButton(
                                        (
                                            "💾 Guardar"
                                            if not self.editing_member_id
                                            else "✅ Actualizar"
                                        ),
                                        on_click=self._on_save_member
                                    ),
                                    CorrectElevatedButton(
                                        "❌ Cancelar",
                                        on_click=self._on_cancel_edit
                                    ) if self.editing_member_id else ft.Container(),
                                ],
                                spacing=10
                            ),
                        ],
                        spacing=15
                    ),
                    padding=20,
                    bgcolor=ft.Colors.PURPLE_50,
                    border=ft.border.all(2, ft.Colors.PURPLE_200),
                    border_radius=10,
                    shadow=ft.BoxShadow(
                        spread_radius=1,
                        blur_radius=6,
                        color=ft.Colors.PURPLE_100,
                    )
                ),
                
                ft.Divider(),
                
                # Lista de miembros
                ft.Text(value="👨‍👩‍👧‍👦 Miembros de la familia", size=20),
                self.members_column,
            ],
            spacing=20,
            scroll=ft.ScrollMode.AUTO
        )
        
        # Cargar datos iniciales
        self._render_members()
        
        return MainLayout(
            page=self.page,
            content=content,
            router=self.router,
        )

    def _on_save_member(self, _: ft.ControlEvent) -> None:
        """Guardar miembro (crear o actualizar)"""
        try:
            # Validar campos obligatorios
            if not self.nombre_input.value:
                self._show_error(AppError(message="El nombre es obligatorio"))
                return
            
            if not self.tipo_ingreso_dropdown.value:
                self._show_error(AppError(message="El tipo de ingreso es obligatorio"))
                return
            
            # Buscar el tipo enum por key
            try:
                selected_tipo = IncomeType[self.tipo_ingreso_dropdown.value]
            except KeyError:
                selected_tipo = IncomeType.NINGUNO
            
            # Validar sueldo si es necesario
            sueldo_mensual = None
            if selected_tipo in (IncomeType.FIJO, IncomeType.MIXTO):
                if not self.sueldo_input.value:
                    self._show_error(
                        AppError(
                            message="El sueldo mensual es obligatorio para este tipo"
                        )
                    )
                    return
                # Limpiar formato: eliminar puntos de separador de miles
                sueldo_str = self.sueldo_input.value.replace(".", "").replace(",", ".")
                sueldo_mensual = float(sueldo_str)
            
            # Crear o actualizar el miembro
            member = FamilyMember(
                id=self.editing_member_id,
                nombre=self.nombre_input.value,
                tipo_ingreso=selected_tipo,
                sueldo_mensual=sueldo_mensual,
                notas=self.notas_input.value if self.notas_input.value else None,
            )
            
            if self.editing_member_id:
                result = self.controller.update_member(member)
                success_msg = "Miembro actualizado correctamente"
            else:
                result = self.controller.add_member(member)
                success_msg = "Miembro guardado correctamente"
            
            match result:
                case Ok(_):
                    self.editing_member_id = None
                    self._clear_inputs()
                    self._render_members()
                    self._show_success(success_msg)
                    self.page.update()
                
                case Err(error):
                    self._show_error(error)
        
        except ValueError:
            self._show_error(AppError(message="El sueldo debe ser un número válido"))

    def _render_members(self) -> None:
        """Renderizar lista de miembros"""
        self.members_column.controls.clear()
        
        members = self.controller.list_active_members()
        
        if not members:
            self.members_column.controls.append(
                ft.Text(value="No hay miembros registrados", italic=True)
            )
        else:
            for member in members:
                sueldo_text = ""
                if member.sueldo_mensual:
                    # Formatear con separador de miles
                    sueldo_formateado = (
                        f"{member.sueldo_mensual:,.0f}".replace(",", ".")
                    )
                    sueldo_text = f" • ${sueldo_formateado}/mes"
                
                self.members_column.controls.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Icon(
                                    icon=ft.Icons.PERSON,
                                    color=ft.Colors.PURPLE_600,
                                    size=30
                                ),
                                ft.Column(
                                    controls=[
                                        ft.Text(
                                            value=member.nombre,
                                            weight=ft.FontWeight.BOLD,
                                            color=ft.Colors.PURPLE_900
                                        ),
                                        ft.Text(
                                            value=f"{member.tipo_ingreso.value}{sueldo_text}",
                                            size=12,
                                            color=ft.Colors.PURPLE_700
                                        ),
                                    ],
                                    spacing=2,
                                    expand=True
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.EDIT,
                                    tooltip="Editar",
                                    icon_color=ft.Colors.DEEP_PURPLE_400,
                                    on_click=lambda e, m=member: self._on_edit_member(m)
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.START
                        ),
                        padding=15,
                        bgcolor=ft.Colors.PURPLE_50,
                        border=ft.border.all(2, ft.Colors.PURPLE_200),
                        border_radius=10,
                        shadow=ft.BoxShadow(
                            spread_radius=1,
                            blur_radius=4,
                            color=ft.Colors.PURPLE_100,
                        )
                    )
                )
        
        self.page.update()

    def _on_edit_member(self, member: FamilyMember) -> None:
        """Cargar datos del miembro para editar"""
        self.editing_member_id = member.id
        self.nombre_input.value = member.nombre
        self.tipo_ingreso_dropdown.value = member.tipo_ingreso.name
        self.sueldo_input.value = (
            str(member.sueldo_mensual) if member.sueldo_mensual else ""
        )
        self.notas_input.value = member.notas if member.notas else ""
        self.page.update()

    def _on_cancel_edit(self, _: ft.ControlEvent) -> None:
        """Cancelar edición"""
        self.editing_member_id = None
        self._clear_inputs()
        self.page.update()

    def _clear_inputs(self) -> None:
        """Limpiar formulario"""
        self.nombre_input.value = ""
        self.tipo_ingreso_dropdown.value = None
        self.sueldo_input.value = ""
        self.notas_input.value = ""

    def _show_error(self, error: AppError) -> None:
        """Mostrar mensaje de error"""
        snack_bar = CorrectSnackBar(
            content=ft.Text(value=f"❌ {error.message}"),
            open=True
        )
        self.page.overlay.append(snack_bar)
        self.page.update()

    def _show_success(self, message: str) -> None:
        """Mostrar mensaje de éxito"""
        snack_bar = CorrectSnackBar(
            content=ft.Text(value=f"✅ {message}"),
            open=True
        )
        self.page.overlay.append(snack_bar)
        self.page.update()
