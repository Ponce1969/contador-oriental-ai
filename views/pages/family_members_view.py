"""
Vista para gestión de miembros de la familia
Arquitectura: State + Sync Pattern (Profesional)
"""

from __future__ import annotations

import flet as ft
from result import Err, Ok

from controllers.family_member_controller import FamilyMemberController
from core.session import SessionManager
from core.state import AppState
from flet_types.flet_types import CorrectElevatedButton, CorrectSnackBar
from models.errors import AppError
from models.family_member_model import FamilyMember
from views.layouts.main_layout import MainLayout


class FamilyMembersView:
    """Vista para gestionar miembros de la familia - State + Sync Pattern"""

    def __init__(self, page: ft.Page, router):
        self.page = page
        self.router = router

        if not SessionManager.is_logged_in(page):
            router.navigate("/login")
            return

        familia_id = SessionManager.get_familia_id(page)
        self.controller = FamilyMemberController(familia_id=familia_id)

        # ===============================
        # STATE CENTRAL
        # ===============================
        self.state = {
            "members": [],  # list[FamilyMember]
            "editing_id": None,  # int | None
            "selected_id": None,  # str | None
        }
        # Type hints para cada acceso
        self._members: list[FamilyMember] = []
        self._editing_id: int | None = None
        self._selected_id: str | None = None

        # ===============================
        # CONTROLS
        # ===============================
        self.select_dropdown = ft.Dropdown(
            label="Seleccionar miembro",
            expand=True,
        )
        self.select_dropdown.on_select = self._on_select
        
        # Botón oculto (ya no necesario, se dispara automáticamente)
        self.load_button = CorrectElevatedButton(
            "🔄 Cargar",
            on_click=self._on_load_click,
            visible=False,
        )

        self.name_input = ft.TextField(label="Nombre", expand=True)

        self.type_dropdown = ft.Dropdown(
            label="Tipo",
            value="persona",
            options=[
                ft.dropdown.Option("persona", "Persona"),
                ft.dropdown.Option("mascota", "Mascota"),
            ],
        )
        self.type_dropdown.on_select = self._on_type_change

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
            ],
        )

        self.especie_input = ft.TextField(
            label="Especie",
            width=200,
            visible=False,
        )

        self.age_input = ft.TextField(
            label="Edad",
            width=100,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        self.job_dropdown = ft.Dropdown(
            label="Estado laboral",
            width=200,
            options=[
                ft.dropdown.Option("empleado", "Empleado"),
                ft.dropdown.Option("estudiante", "Estudiante"),
                ft.dropdown.Option("jubilado", "Jubilado"),
                ft.dropdown.Option("desempleado", "Desempleado"),
                ft.dropdown.Option("independiente", "Independiente"),
            ],
        )

        self.notes_input = ft.TextField(
            label="Notas",
            multiline=True,
            expand=True,
        )

        self.members_column = ft.Column(spacing=10)

        # Load inicial
        self._load_members()

    # =====================================================
    # DATA
    # =====================================================
    def _load_members(self):
        self.state["members"] = self.controller.list_active_members()

    # =====================================================
    # RENDER
    # =====================================================
    def render(self):
        is_mobile = AppState.device == "mobile"
        col_half = {"xs": 12, "sm": 6}
        col_third = {"xs": 12, "sm": 4}

        content = ft.Column(
            controls=[
                ft.Text(
                    self.controller.get_title(),
                    size=20 if is_mobile else 26,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Divider(),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    self.select_dropdown,
                                    self.load_button,
                                ],
                                spacing=10,
                            ),
                            ft.ResponsiveRow(
                                controls=[
                                    ft.Container(
                                        content=self.name_input,
                                        col={"xs": 12, "sm": 5},
                                    ),
                                    ft.Container(
                                        content=self.type_dropdown,
                                        col=col_third,
                                    ),
                                    ft.Container(
                                        content=self.age_input,
                                        col={"xs": 6, "sm": 2},
                                    ),
                                ],
                                spacing=10,
                                run_spacing=10,
                            ),
                            ft.ResponsiveRow(
                                controls=[
                                    ft.Container(
                                        content=self.parentesco_dropdown,
                                        col=col_half,
                                    ),
                                    ft.Container(
                                        content=self.job_dropdown,
                                        col=col_half,
                                    ),
                                ],
                                spacing=10,
                                run_spacing=10,
                            ),
                            self.especie_input,
                            self.notes_input,
                            ft.Row(
                                controls=[
                                    CorrectElevatedButton(
                                        "Guardar",
                                        on_click=self._on_save,
                                    ),
                                    CorrectElevatedButton(
                                        "Cancelar",
                                        on_click=self._on_cancel,
                                    ),
                                ],
                                spacing=10,
                            ),
                        ],
                        spacing=12,
                    ),
                    padding=16 if is_mobile else 20,
                    bgcolor=ft.Colors.PURPLE_50,
                    border=ft.border.all(2, ft.Colors.PURPLE_200),
                    border_radius=10,
                ),
                ft.Divider(),
                ft.Text(
                    "👨‍👩‍👧‍👦 Miembros",
                    size=16 if is_mobile else 20,
                ),
                self.members_column,
            ],
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
        )

        # Handlers - Usar on_select según documentación de Fleting
        self.select_dropdown.on_select = self._on_select
        
        # Sync inicial
        self._sync_ui()

        return MainLayout(
            page=self.page,
            content=content,
            router=self.router,
        )

    # =====================================================
    # SYNC
    # =====================================================
    def _sync_ui(self):
        # Dropdown
        self.select_dropdown.options = [
            ft.dropdown.Option(
                key=str(m.id),
                text=f"{m.nombre} ({m.tipo_miembro})",
            )
            for m in self.state["members"]
        ]
        self.select_dropdown.value = self.state["selected_id"]
        
        # Workaround: Forzar update individual del dropdown
        # (bug conocido de Flet donde value no se refleja visualmente)
        try:
            self.select_dropdown.update()
        except:
            pass  # Control aún no está en la página

        # Form
        if self.state["editing_id"]:
            member = self._get_member(self.state["editing_id"])
            if member:
                self._fill_form(member)
        else:
            self._clear_form()

        # List
        self._render_list()
        
        # Workaround: Forzar updates individuales de todos los campos
        # (bug conocido de Flet donde los controles no se actualizan visualmente)
        try:
            self.name_input.update()
            self.type_dropdown.update()
            self.parentesco_dropdown.update()
            self.especie_input.update()
            self.age_input.update()
            self.job_dropdown.update()
            self.notes_input.update()
        except:
            pass  # Controles aún no están en la página

        self.page.update()

    # =====================================================
    # FORM
    # =====================================================
    def _fill_form(self, m: FamilyMember):
        self.name_input.value = m.nombre
        self.type_dropdown.value = m.tipo_miembro or "persona"
        self.parentesco_dropdown.value = m.parentesco
        self.especie_input.value = m.especie or ""
        self.age_input.value = str(m.edad or "")
        self.job_dropdown.value = m.estado_laboral
        self.notes_input.value = m.notas or ""

        self._update_visibility()

    def _clear_form(self):
        self.name_input.value = ""
        self.type_dropdown.value = "persona"
        self.parentesco_dropdown.value = None
        self.especie_input.value = ""
        self.age_input.value = ""
        self.job_dropdown.value = None
        self.notes_input.value = ""

        self._update_visibility()

    def _update_visibility(self):
        is_person = self.type_dropdown.value == "persona"

        self.parentesco_dropdown.visible = is_person
        self.job_dropdown.visible = is_person
        self.especie_input.visible = not is_person

    # =====================================================
    # LIST
    # =====================================================
    def _render_list(self):
        self.members_column.controls.clear()

        for m in self.state["members"]:
            # Construir texto descriptivo
            edad_text = f"{m.edad} años" if m.edad else "Edad no especificada"
            
            if m.tipo_miembro == "mascota":
                especie_text = m.especie.capitalize() if m.especie else "Mascota"
                info_text = f"🐾 {especie_text} • {edad_text}"
                icon = ft.Icons.PETS
            else:
                parentesco_text = m.parentesco.capitalize() if m.parentesco else "Otro"
                estado_text = m.estado_laboral.capitalize() if m.estado_laboral else "No especificado"
                info_text = f"{parentesco_text} • {edad_text} • {estado_text}"
                icon = ft.Icons.PERSON

            self.members_column.controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(icon=icon, color=ft.Colors.PURPLE_600, size=30),
                            ft.Column(
                                controls=[
                                    ft.Text(
                                        m.nombre,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.PURPLE_900,
                                    ),
                                    ft.Text(
                                        info_text,
                                        size=12,
                                        color=ft.Colors.PURPLE_700,
                                    ),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.EDIT,
                                tooltip="Editar",
                                icon_color=ft.Colors.DEEP_PURPLE_400,
                                on_click=lambda e, mm=m: self._on_edit(mm),
                            ),
                        ]
                    ),
                    padding=15,
                    bgcolor=ft.Colors.PURPLE_50,
                    border=ft.border.all(2, ft.Colors.PURPLE_200),
                    border_radius=10,
                )
            )

    # =====================================================
    # HELPERS
    # =====================================================
    def _get_member(self, member_id: int):
        for m in self.state["members"]:
            if m.id == member_id:
                return m
        return None

    # =====================================================
    # EVENTS
    # =====================================================
    def _on_select(self, e):
        """Handler para on_change del dropdown - dispara carga automática"""
        # Disparar automáticamente la carga de datos sin necesidad del botón
        self._on_load_click(e)
    
    def _on_load_click(self, e):
        """Cargar datos del miembro seleccionado al hacer clic en el botón"""
        if not self.select_dropdown.value:
            return

        self.state["selected_id"] = self.select_dropdown.value
        self.state["editing_id"] = int(self.select_dropdown.value)

        self._sync_ui()

    def _on_edit(self, member: FamilyMember):
        self.state["editing_id"] = member.id
        self.state["selected_id"] = str(member.id)  # Convertir a str para compatibilidad

        self._sync_ui()

    def _on_type_change(self, e):
        self._update_visibility()
        self.page.update()

    def _on_save(self, e):
        if not self.name_input.value:
            self._error("Nombre obligatorio")
            return

        # Validaciones según tipo
        tipo = self.type_dropdown.value
        if tipo == "persona":
            if not self.parentesco_dropdown.value:
                self._error("Parentesco obligatorio para personas")
                return
            if not self.job_dropdown.value:
                self._error("Estado laboral obligatorio para personas")
                return
        else:
            if not self.especie_input.value:
                self._error("Especie obligatoria para mascotas")
                return

        # Validar edad
        edad = None
        if self.age_input.value:
            try:
                edad = int(self.age_input.value)
                if edad < 0 or edad > 150:
                    self._error("Edad debe estar entre 0 y 150")
                    return
            except ValueError:
                self._error("Edad debe ser un número")
                return

        member = FamilyMember(
            id=self.state["editing_id"],
            nombre=self.name_input.value,
            tipo_miembro=tipo,
            parentesco=self.parentesco_dropdown.value if tipo == "persona" else None,
            especie=self.especie_input.value if tipo == "mascota" else None,
            edad=edad,
            estado_laboral=self.job_dropdown.value if tipo == "persona" else None,
            notas=self.notes_input.value if self.notes_input.value else None,
        )

        if self.state["editing_id"]:
            result = self.controller.update_member(member)
        else:
            result = self.controller.add_member(member)

        if isinstance(result, Err):
            self._error(result.err_value.message)
            return

        # Reload
        self._load_members()

        self.state["editing_id"] = None
        self.state["selected_id"] = None

        self._sync_ui()

        self._success("Guardado")

    def _on_cancel(self, e):
        self.state["editing_id"] = None
        self.state["selected_id"] = None

        self._sync_ui()

    # =====================================================
    # FEEDBACK
    # =====================================================
    def _error(self, msg: str):
        self.page.snack_bar = CorrectSnackBar(
            content=ft.Text(f"❌ {msg}"),
            open=True,
        )
        self.page.update()

    def _success(self, msg: str):
        self.page.snack_bar = CorrectSnackBar(
            content=ft.Text(f"✅ {msg}"),
            open=True,
        )
        self.page.update()
