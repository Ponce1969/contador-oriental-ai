"""
Vista para gestión de miembros de la familia
Arquitectura: State + Sync Pattern (Profesional)
"""

from decimal import Decimal
from typing import Any

import flet as ft
from result import Err

from constants.responsive import Responsive
from controllers.family_member_controller import FamilyMemberController
from controllers.labor_controller import LaborController
from core.session import SessionManager
from core.state import AppState
from flet_types.flet_types import CorrectElevatedButton, CorrectSnackBar
from models.family_member_model import FamilyMember
from services.labor.domain.enums import ActivityNature
from services.labor.domain.models import EconomicActivity
from services.labor.engine import LaborCalculationEngine
from utils.formatters import format_currency
from views.components.benefits_projection_card import BenefitsProjectionCard
from views.components.labor_simulator_card import LaborSimulatorCard
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
        self.labor_controller = LaborController(familia_id=familia_id)
        self.simulator_card = LaborSimulatorCard(
            page=self.page,
            familia_id=familia_id,
            on_activity_saved=self._on_activity_saved,
        )
        self.benefits_card = BenefitsProjectionCard(
            labor_controller=self.labor_controller,
            member_controller=self.controller,
            show_header=False,
        )

        # ===============================
        # STATE CENTRAL
        # ===============================
        self.state: dict[str, Any] = {
            "members": [],  # list[FamilyMember]
            "activities_map": {},  # dict[int, EconomicActivity]
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
            hint_text="ej: 10",
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
        activities = self.labor_controller.list_all_activities()
        self.state["activities_map"] = {
            act.family_member_id: act for act in activities if act.is_active
        }
        self.simulator_card.set_available_members(self.state["members"])
        self.benefits_card.refresh()

    # =====================================================
    # RENDER
    # =====================================================
    def render(self):
        is_mobile = AppState.device == "mobile"

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
                                        col=Responsive.COL_THIRD,
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
                                        col=Responsive.COL_HALF,
                                    ),
                                    ft.Container(
                                        content=self.job_dropdown,
                                        col=Responsive.COL_HALF,
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
                    border=ft.Border.all(2, ft.Colors.PURPLE_200),
                    border_radius=10,
                ),
                ft.Divider(),
                ft.Text(
                    "👨‍👩‍👧‍👦 Miembros",
                    size=16 if is_mobile else 20,
                ),
                self.members_column,
                ft.Divider(),
            ],
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
        )

        self.benefits_tile = ft.ExpansionTile(
            leading=ft.Icon(
                ft.Icons.CARD_GIFTCARD,
                color=ft.Colors.PURPLE_700,
            ),
            title=ft.Text(
                "Previsión de Aguinaldo y Salario Vacacional",
                weight=ft.FontWeight.BOLD,
                size=15,
                color=ft.Colors.PURPLE_900,
            ),
            subtitle=ft.Text(
                "Abrir para ver el próximo aguinaldo (SAC) y salario vacacional por integrante",
                size=12,
                color=ft.Colors.PURPLE_700,
            ),
            expanded=False,
            controls=[
                ft.Container(
                    content=self.benefits_card,
                    padding=ft.Padding.only(top=6, bottom=6),
                )
            ],
            bgcolor=ft.Colors.PURPLE_50,
            collapsed_bgcolor=ft.Colors.PURPLE_50,
            collapsed_icon_color=ft.Colors.PURPLE_700,
            icon_color=ft.Colors.PURPLE_700,
            shape=ft.RoundedRectangleBorder(radius=10),
            collapsed_shape=ft.RoundedRectangleBorder(radius=10),
        )
        content.controls.append(self.benefits_tile)

        self.simulator_tile = ft.ExpansionTile(
            leading=ft.Icon(
                ft.Icons.CALCULATE_OUTLINED,
                color=ft.Colors.INDIGO_700,
            ),
            title=ft.Text(
                "Simulador de Sueldos y Regímenes Laborales",
                weight=ft.FontWeight.BOLD,
                size=15,
                color=ft.Colors.INDIGO_900,
            ),
            subtitle=ft.Text(
                "Abrir para calcular retenciones IRPF, BPS/CJPPU y líquido en mano",
                size=12,
                color=ft.Colors.INDIGO_700,
            ),
            expanded=False,
            controls=[
                ft.Container(
                    content=self.simulator_card.render(),
                    padding=ft.Padding.only(top=6, bottom=6),
                )
            ],
            bgcolor=ft.Colors.INDIGO_50,
            collapsed_bgcolor=ft.Colors.INDIGO_50,
            collapsed_icon_color=ft.Colors.INDIGO_700,
            icon_color=ft.Colors.INDIGO_700,
            shape=ft.RoundedRectangleBorder(radius=10),
            collapsed_shape=ft.RoundedRectangleBorder(radius=10),
        )
        content.controls.append(self.simulator_tile)

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
        members_list: list[FamilyMember] = self.state.get("members") or []
        self.select_dropdown.options = [
            ft.dropdown.Option(
                key=str(m.id),
                text=f"{m.nombre} ({m.tipo_miembro})",
            )
            for m in members_list
        ]
        self.select_dropdown.value = self.state["selected_id"]

        # Workaround: Forzar update individual del dropdown
        # (bug conocido de Flet donde value no se refleja visualmente)
        try:
            self.select_dropdown.update()
        except Exception:
            pass  # Control aún no está en la página

        # Form
        editing_id = self.state.get("editing_id")
        if isinstance(editing_id, int):
            member = self._get_member(editing_id)
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
        except Exception:
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

        members_list: list[FamilyMember] = self.state.get("members") or []
        activities_map: dict[int, EconomicActivity] = (
            self.state.get("activities_map") or {}
        )

        for m in members_list:
            edad_text = f"{m.edad} años" if m.edad else "Edad no especificada"

            if m.tipo_miembro == "mascota":
                especie_text = m.especie.capitalize() if m.especie else "Mascota"
                info_text = f"🐾 {especie_text} • {edad_text}"
                icon = ft.Icons.PETS
            else:
                parentesco_text = m.parentesco.capitalize() if m.parentesco else "Otro"
                estado_text = (
                    m.estado_laboral.capitalize()
                    if m.estado_laboral
                    else "No especificado"
                )
                info_text = f"{parentesco_text} • {edad_text} • {estado_text}"
                icon = ft.Icons.PERSON

            act_badges = []
            if m.id and m.id in activities_map:
                act = activities_map[m.id]
                if act.nature == ActivityNature.DEPENDIENTE and act.dependent_details:
                    nom = act.dependent_details.estimated_monthly_nominal or Decimal(
                        "0"
                    )
                    withh = LaborCalculationEngine.calculate_withholdings(
                        nominal=nom,
                        profile=act.dependent_details.tax_profile,
                    )
                    nom_fmt = format_currency(nom, "UYU")
                    liq_fmt = format_currency(withh.liquid_amount, "UYU")
                    act_badges.append(
                        ft.Container(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(
                                        ft.Icons.WORK_OUTLINE,
                                        size=13,
                                        color=ft.Colors.INDIGO_800,
                                    ),
                                    ft.Text(
                                        f"Dependiente: {nom_fmt} nom. | "
                                        f"{liq_fmt} en mano",
                                        size=11,
                                        weight=ft.FontWeight.W_500,
                                        color=ft.Colors.INDIGO_900,
                                    ),
                                ],
                                spacing=4,
                            ),
                            bgcolor=ft.Colors.LIGHT_BLUE_50,
                            border=ft.Border.all(1, ft.Colors.LIGHT_BLUE_200),
                            border_radius=6,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                        )
                    )
                elif act.nature == ActivityNature.INDEPENDIENTE:
                    act_badges.append(
                        ft.Container(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(
                                        ft.Icons.BUILD_OUTLINE,
                                        size=13,
                                        color=ft.Colors.INDIGO_800,
                                    ),
                                    ft.Text(
                                        f"{act.title}",
                                        size=11,
                                        weight=ft.FontWeight.W_500,
                                        color=ft.Colors.INDIGO_900,
                                    ),
                                ],
                                spacing=4,
                            ),
                            bgcolor=ft.Colors.LIGHT_BLUE_50,
                            border=ft.Border.all(1, ft.Colors.LIGHT_BLUE_200),
                            border_radius=6,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                        )
                    )
                elif act.nature == ActivityNature.PASIVIDAD:
                    act_badges.append(
                        ft.Container(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(
                                        ft.Icons.SAVINGS_OUTLINED,
                                        size=13,
                                        color=ft.Colors.INDIGO_800,
                                    ),
                                    ft.Text(
                                        f"{act.title}",
                                        size=11,
                                        weight=ft.FontWeight.W_500,
                                        color=ft.Colors.INDIGO_900,
                                    ),
                                ],
                                spacing=4,
                            ),
                            bgcolor=ft.Colors.LIGHT_BLUE_50,
                            border=ft.Border.all(1, ft.Colors.LIGHT_BLUE_200),
                            border_radius=6,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                        )
                    )

            col_controls: list[ft.Control] = [
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
            ]
            if act_badges:
                col_controls.extend(act_badges)

            actions = []
            if m.tipo_miembro == "persona":
                actions.append(
                    ft.IconButton(
                        icon=ft.Icons.CALCULATE_OUTLINED,
                        tooltip="Simular / Configurar Actividad Laboral",
                        icon_color=ft.Colors.INDIGO_700,
                        on_click=lambda e, mm=m: self._on_simulate_member(mm),
                    )
                )
            actions.extend(
                [
                    ft.IconButton(
                        icon=ft.Icons.EDIT,
                        tooltip="Editar",
                        icon_color=ft.Colors.DEEP_PURPLE_400,
                        on_click=lambda e, mm=m: self._on_edit(mm),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.PERSON_OFF,
                        tooltip="Desvincular",
                        icon_color=ft.Colors.RED_400,
                        on_click=lambda e, mm=m: self._on_unlink_confirm(mm),
                    ),
                ]
            )

            self.members_column.controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(icon=icon, color=ft.Colors.PURPLE_600, size=30),
                            ft.Column(
                                controls=col_controls,
                                spacing=3,
                                expand=True,
                            ),
                            *actions,
                        ]
                    ),
                    padding=15,
                    bgcolor=ft.Colors.PURPLE_50,
                    border=ft.Border.all(1.5, ft.Colors.PURPLE_200),
                    border_radius=10,
                    shadow=ft.BoxShadow(
                        spread_radius=1,
                        blur_radius=6,
                        color=ft.Colors.BLUE_GREY_100,
                        offset=ft.Offset(0, 2),
                    ),
                )
            )

    # =====================================================
    # HELPERS
    # =====================================================
    def _get_member(self, member_id: int):
        members_list: list[FamilyMember] = self.state.get("members") or []
        for m in members_list:
            if m.id == member_id:
                return m
        return None

    # =====================================================
    # EVENTS
    # =====================================================
    def _on_simulate_member(self, member: FamilyMember):
        """Abre el simulador y lo sincroniza con el integrante seleccionado."""
        self.simulator_card.set_target_member(member.id, member.nombre)
        if hasattr(self, "simulator_tile") and self.simulator_tile:
            self.simulator_tile.expanded = True
            try:
                self.simulator_tile.update()
            except Exception:
                pass
        self.page.update()

    def _on_activity_saved(self, saved_act: EconomicActivity):
        """Callback cuando se guarda una actividad económica desde el simulador."""
        self._load_members()
        self._sync_ui()

    def _on_select(self, e):
        """Handler para on_change del dropdown - dispara carga automática"""
        self._on_load_click(e)

    def _on_load_click(self, e):
        """Cargar datos del miembro seleccionado al hacer clic en el botón"""
        if not self.select_dropdown.value:
            return

        self.state["selected_id"] = self.select_dropdown.value
        self.state["editing_id"] = int(self.select_dropdown.value)
        member = self._get_member(self.state["editing_id"])
        if member:
            self.simulator_card.set_target_member(member.id, member.nombre)

        self._sync_ui()

    def _on_edit(self, member: FamilyMember):
        self.state["editing_id"] = member.id
        self.state["selected_id"] = str(member.id)
        self.simulator_card.set_target_member(member.id, member.nombre)

        self._sync_ui()

    def _on_unlink_confirm(self, member: FamilyMember):
        """Mostrar diálogo de confirmación antes de desvincular."""

        def on_confirm(e):
            dlg.open = False
            self.page.update()
            self._on_unlink(member)

        def on_cancel(e):
            dlg.open = False
            self.page.update()

        dlg = ft.AlertDialog(
            title=ft.Text(f"¿Desvincular a {member.nombre}?"),
            content=ft.Text(
                "El miembro ya no aparecerá en las listas activas ni generará "
                "ingresos/gastos recurrentes. Su historial pasado se conservará "
                "para mantener la precisión de los balances."
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=on_cancel),
                ft.ElevatedButton(
                    "Confirmar Desvinculación",
                    bgcolor=ft.Colors.RED_600,
                    color=ft.Colors.WHITE,
                    on_click=on_confirm,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _on_unlink(self, member: FamilyMember):
        """Ejecutar desvinculación del miembro."""
        if member.id is None:
            return
        result = self.controller.deactivate_member(member.id)
        if result.is_err():
            self._error(f"Error al desvincular: {result.unwrap_err().message}")
            return

        # Recargar lista
        self.state["members"] = self.controller.list_active_members()
        self._sync_ui()
        self.page.snack_bar = ft.SnackBar(
            ft.Text(f"{member.nombre} desvinculado correctamente"),
            bgcolor=ft.Colors.GREEN_600,
        )
        self.page.snack_bar.open = True
        self.page.update()

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

        # Validar edad — limpiar texto extra como "10 años" → "10"
        edad = None
        if self.age_input.value:
            edad_str = "".join(c for c in self.age_input.value if c.isdigit())
            try:
                edad = int(edad_str)
                if edad < 0 or edad > 150:
                    self._error("Edad debe estar entre 0 y 150")
                    return
            except ValueError:
                self._error("Edad debe ser un número")
                return

        editing_id = self.state.get("editing_id")
        member_id = editing_id if isinstance(editing_id, int) else None
        member = FamilyMember(
            id=member_id,
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
