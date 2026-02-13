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
from models.family_member_model import FamilyMember
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
        
        # Cargar miembros existentes para el dropdown
        self.existing_members = self.controller.list_active_members()
        
        # Dropdown para seleccionar miembro existente
        self.select_member_dropdown = ft.Dropdown(
            label="Seleccionar miembro existente (para editar)",
            width=400,
            hint_text="Busca y selecciona un miembro para editar",
            options=[
                ft.dropdown.Option(key=str(member.id), text=f"{member.nombre} ({member.tipo_miembro})")
                for member in self.existing_members
            ]
        )
        self.select_member_dropdown.on_change = self._on_select_member
        
        # Campos del formulario
        self.nombre_input = ft.TextField(
            label="Nombre",
            hint_text="Ej: Juan Pérez o Firulais",
            width=300
        )
        
        self.tipo_miembro_dropdown = ft.Dropdown(
            label="Tipo",
            width=150,
            value="persona",
            options=[
                ft.dropdown.Option("persona", "Persona"),
                ft.dropdown.Option("mascota", "Mascota"),
            ]
        )
        self.tipo_miembro_dropdown.on_change = self._on_tipo_miembro_change
        
        self.parentesco_dropdown = ft.Dropdown(
            label="Parentesco",
            width=200,
            options=[
                ft.dropdown.Option("padre", "Padre"),
                ft.dropdown.Option("madre", "Madre"),
                ft.dropdown.Option("hijo", "Hijo"),
                ft.dropdown.Option("hija", "Hija"),
                ft.dropdown.Option("abuelo", "Abuelo"),
                ft.dropdown.Option("abuela", "Abuela"),
                ft.dropdown.Option("otro", "Otro"),
            ]
        )
        
        self.especie_input = ft.TextField(
            label="Especie",
            hint_text="Ej: Gato, Perro, Pájaro",
            width=200,
            visible=False
        )
        
        self.edad_input = ft.TextField(
            label="Edad",
            hint_text="Ej: 35",
            width=100,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        self.estado_laboral_dropdown = ft.Dropdown(
            label="Estado laboral",
            width=200,
            options=[
                ft.dropdown.Option("empleado", "Empleado"),
                ft.dropdown.Option("desempleado", "Desempleado"),
                ft.dropdown.Option("jubilado", "Jubilado"),
                ft.dropdown.Option("estudiante", "Estudiante"),
                ft.dropdown.Option("independiente", "Independiente/Autónomo"),
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
                            self.select_member_dropdown,
                            ft.Divider(),
                            ft.Row(
                                controls=[
                                    self.nombre_input,
                                    self.tipo_miembro_dropdown,
                                    self.edad_input,
                                ],
                                spacing=10
                            ),
                            ft.Row(
                                controls=[
                                    self.parentesco_dropdown,
                                    self.estado_laboral_dropdown,
                                ],
                                spacing=10
                            ),
                            ft.Row(
                                controls=[
                                    self.especie_input,
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
            
            # Validar campos según tipo de miembro
            tipo_miembro = self.tipo_miembro_dropdown.value or "persona"
            
            if tipo_miembro == "persona":
                if not self.parentesco_dropdown.value:
                    self._show_error(AppError(message="El parentesco es obligatorio para personas"))
                    return
                
                if not self.estado_laboral_dropdown.value:
                    self._show_error(AppError(message="El estado laboral es obligatorio para personas"))
                    return
            else:
                if not self.especie_input.value:
                    self._show_error(AppError(message="La especie es obligatoria para mascotas"))
                    return
            
            # Validar edad
            edad = None
            if self.edad_input.value:
                try:
                    edad = int(self.edad_input.value)
                    if edad < 0 or edad > 150:
                        self._show_error(AppError(message="La edad debe estar entre 0 y 150"))
                        return
                except ValueError:
                    self._show_error(AppError(message="La edad debe ser un número válido"))
                    return
            
            # Crear o actualizar el miembro
            member = FamilyMember(
                id=self.editing_member_id,
                nombre=self.nombre_input.value,
                tipo_miembro=tipo_miembro,
                parentesco=self.parentesco_dropdown.value if tipo_miembro == "persona" else None,
                especie=self.especie_input.value if tipo_miembro == "mascota" else None,
                edad=edad,
                estado_laboral=self.estado_laboral_dropdown.value if tipo_miembro == "persona" else None,
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
        
        except Exception as e:
            self._show_error(AppError(message=f"Error al guardar: {str(e)}"))

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
                # Construir texto descriptivo según tipo
                edad_text = f"{member.edad} años" if member.edad else "Edad no especificada"
                
                if member.tipo_miembro == "mascota":
                    especie_text = member.especie.capitalize() if member.especie else "Mascota"
                    info_text = f"🐾 {especie_text} • {edad_text}"
                    icon = ft.Icons.PETS
                else:
                    parentesco_text = member.parentesco.capitalize() if member.parentesco else "Otro"
                    estado_text = member.estado_laboral.capitalize() if member.estado_laboral else "No especificado"
                    info_text = f"{parentesco_text} • {edad_text} • {estado_text}"
                    icon = ft.Icons.PERSON
                
                self.members_column.controls.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Icon(
                                    icon=icon,
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
                                            value=info_text,
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

    def _on_select_member(self, e: ft.ControlEvent) -> None:
        """Cargar datos del miembro seleccionado automáticamente"""
        if not self.select_member_dropdown.value:
            return
        
        member_id = int(self.select_member_dropdown.value)
        
        # Buscar el miembro en la lista existente
        for member in self.existing_members:
            if member.id == member_id:
                self._on_edit_member(member)
                break
    
    def _on_edit_member(self, member: FamilyMember) -> None:
        """Cargar datos del miembro para editar"""
        self.editing_member_id = member.id
        self.nombre_input.value = member.nombre
        self.tipo_miembro_dropdown.value = member.tipo_miembro if member.tipo_miembro else "persona"
        self.parentesco_dropdown.value = member.parentesco if member.parentesco else None
        self.especie_input.value = member.especie if member.especie else ""
        self.edad_input.value = str(member.edad) if member.edad else ""
        self.estado_laboral_dropdown.value = member.estado_laboral if member.estado_laboral else None
        self.notas_input.value = member.notas if member.notas else ""
        self._update_fields_visibility()
        self.page.update()

    def _on_cancel_edit(self, _: ft.ControlEvent) -> None:
        """Cancelar edición"""
        self.editing_member_id = None
        self._clear_inputs()
        self.page.update()

    def _on_tipo_miembro_change(self, e: ft.ControlEvent) -> None:
        """Manejar cambio de tipo de miembro"""
        self._update_fields_visibility()
        self.page.update()
    
    def _update_fields_visibility(self) -> None:
        """Actualizar visibilidad de campos según tipo de miembro"""
        es_persona = self.tipo_miembro_dropdown.value == "persona"
        self.parentesco_dropdown.visible = es_persona
        self.estado_laboral_dropdown.visible = es_persona
        self.especie_input.visible = not es_persona
    
    def _clear_inputs(self) -> None:
        """Limpiar formulario"""
        self.select_member_dropdown.value = None
        self.nombre_input.value = ""
        self.tipo_miembro_dropdown.value = "persona"
        self.parentesco_dropdown.value = None
        self.especie_input.value = ""
        self.edad_input.value = ""
        self.estado_laboral_dropdown.value = None
        self.notas_input.value = ""
        self._update_fields_visibility()
        
        # Recargar lista de miembros en el dropdown
        self.existing_members = self.controller.list_active_members()
        self.select_member_dropdown.options = [
            ft.dropdown.Option(
                key=str(member.id), 
                text=f"{member.nombre} ({member.tipo_miembro})"
            )
            for member in self.existing_members
        ]

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
