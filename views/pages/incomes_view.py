"""
Vista para gestión de ingresos familiares
"""

from __future__ import annotations

from datetime import date

import flet as ft
from result import Err, Ok

from constants.responsive import Responsive
from controllers.family_member_controller import FamilyMemberController
from controllers.income_controller import IncomeController
from core.session import SessionManager
from core.state import AppState
from flet_types.flet_types import CorrectElevatedButton, CorrectSnackBar
from models.errors import AppError
from models.income_model import Income, IncomeCategory, RecurrenceFrequency
from utils.formatters import format_currency
from views.layouts.main_layout import MainLayout


class IncomesView:
    """Vista para registrar ingresos familiares"""
    
    def __init__(self, page, router):
        self.page = page
        self.router = router
        
        # Verificar login
        if not SessionManager.is_logged_in(page):
            router.navigate("/login")
            return
        
        # Obtener familia_id de la sesión
        familia_id = SessionManager.get_familia_id(page)
        
        # Controllers
        self.income_controller = IncomeController(familia_id=familia_id)
        self.member_controller = FamilyMemberController(familia_id=familia_id)
        
        # Cargar miembros activos
        self.active_members = self.member_controller.list_active_members()
        
        # Campos del formulario
        self.member_dropdown = ft.Dropdown(
            label="Miembro de la familia",
            expand=True,
            options=[
                ft.dropdown.Option(key=str(member.id), text=member.nombre)
                for member in self.active_members
            ],
        )

        self.monto_input = ft.TextField(
            label="Monto ($)",
            hint_text="Ej: 50.000 o 50000",
            expand=True,
        )

        self.descripcion_input = ft.TextField(
            label="Descripción",
            hint_text="Ej: Jornal día 15, Cobro de sueldo enero",
            expand=True,
        )

        self.categoria_dropdown = ft.Dropdown(
            label="Categoría",
            expand=True,
            options=[
                ft.dropdown.Option(key=cat.name, text=cat.value)
                for cat in IncomeCategory
            ],
        )

        self.fecha_input = ft.TextField(
            label="Fecha (YYYY-MM-DD)",
            hint_text=str(date.today()),
            value=str(date.today()),
            expand=True,
        )

        self.notas_input = ft.TextField(
            label="Notas (opcional)",
            hint_text="Ej: Mensual, Quincenal, Jornal diario, etc.",
            multiline=True,
            min_lines=2,
            max_lines=3,
            expand=True,
        )

        self.recurrente_checkbox = ft.Checkbox(
            label="Ingreso recurrente (sueldo, alquiler, etc.)",
            value=False,
            on_change=self._on_recurrente_changed,
        )

        self.frecuencia_dropdown = ft.Dropdown(
            label="Frecuencia de cobro",
            expand=True,
            visible=False,
            options=[
                ft.dropdown.Option(key=f.name, text=f.value)
                for f in RecurrenceFrequency
            ],
        )

        # Lista de ingresos
        self.incomes_column = ft.Column(spacing=10)
        
        # Resumen
        self.summary_column = ft.Column(spacing=5)
        
        # Estado de edición
        self.editing_income_id = None

    def render(self):
        """Renderizar la vista completa"""
        is_mobile = AppState.device == "mobile"

        content = ft.Column(
            controls=[
                ft.Text(
                    value=self.income_controller.get_title(),
                    size=20 if is_mobile else 28,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Divider(),

                # Formulario de registro
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                value=(
                                    "💰 Registrar ingreso"
                                    if not self.editing_income_id
                                    else "✏️ Editar ingreso"
                                ),
                                size=16 if is_mobile else 20,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.TEAL_700,
                            ),
                            ft.ResponsiveRow(
                                controls=[
                                    ft.Container(
                                        content=self.member_dropdown,
                                        col=Responsive.COL_HALF,
                                    ),
                                    ft.Container(
                                        content=self.categoria_dropdown,
                                        col=Responsive.COL_HALF,
                                    ),
                                    ft.Container(
                                        content=self.monto_input,
                                        col=Responsive.COL_HALF,
                                    ),
                                    ft.Container(
                                        content=self.fecha_input,
                                        col=Responsive.COL_HALF,
                                    ),
                                ],
                                spacing=10,
                                run_spacing=10,
                            ),
                            self.descripcion_input,
                            self.notas_input,
                            self.recurrente_checkbox,
                            self.frecuencia_dropdown,
                            ft.Row(
                                controls=[
                                    CorrectElevatedButton(
                                        (
                                            "💾 Guardar"
                                            if not self.editing_income_id
                                            else "✅ Actualizar"
                                        ),
                                        on_click=self._on_save_income,
                                    ),
                                    CorrectElevatedButton(
                                        "❌ Cancelar",
                                        on_click=self._on_cancel_edit,
                                    ) if self.editing_income_id else ft.Container(),
                                ],
                                spacing=10,
                            ),
                        ],
                        spacing=12,
                    ),
                    padding=16 if is_mobile else 20,
                    bgcolor=ft.Colors.CYAN_50,
                    border=ft.border.all(2, ft.Colors.TEAL_200),
                    border_radius=10,
                    shadow=ft.BoxShadow(
                        spread_radius=1,
                        blur_radius=6,
                        color=ft.Colors.TEAL_100,
                    ),
                ),

                ft.Divider(),

                ft.Text(
                    value="📊 Resumen por categorías",
                    size=16 if is_mobile else 20,
                ),
                self.summary_column,

                ft.Divider(),

                ft.Text(
                    value="💵 Ingresos registrados",
                    size=16 if is_mobile else 20,
                ),
                self.incomes_column,
            ],
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
        )

        # Cargar datos iniciales
        self._render_incomes()
        self._render_summary()

        return MainLayout(
            page=self.page,
            content=content,
            router=self.router,
        )

    def _on_recurrente_changed(self, e: ft.ControlEvent) -> None:
        """Mostrar/ocultar dropdown de frecuencia según checkbox."""
        self.frecuencia_dropdown.visible = bool(e.control.value)
        self.page.update()

    def _on_save_income(self, _: ft.ControlEvent) -> None:
        """Guardar ingreso (crear o actualizar)"""
        try:
            # Validar campos obligatorios
            if not self.member_dropdown.value:
                self._show_error(AppError(message="Debe seleccionar un miembro"))
                return
            
            if not self.monto_input.value:
                self._show_error(AppError(message="El monto es obligatorio"))
                return
            
            if not self.descripcion_input.value:
                self._show_error(AppError(message="La descripción es obligatoria"))
                return
            
            if not self.categoria_dropdown.value:
                self._show_error(AppError(message="La categoría es obligatoria"))
                return
            
            # Parsear fecha
            try:
                fecha = date.fromisoformat(self.fecha_input.value)
            except ValueError:
                self._show_error(
                    AppError(
                        message="Fecha inválida. Use formato YYYY-MM-DD"
                    )
                )
                return
            
            # Parsear monto (limpiar formato: eliminar puntos de separador de miles)
            try:
                monto_str = self.monto_input.value.replace(".", "").replace(",", ".")
                monto = float(monto_str)
            except ValueError:
                self._show_error(AppError(message="El monto debe ser un número válido"))
                return
            
            # Obtener categoría
            try:
                categoria = IncomeCategory[self.categoria_dropdown.value]
            except KeyError:
                self._show_error(AppError(message="Categoría inválida"))
                return
            
            # Crear o actualizar el ingreso
            es_recurrente = bool(self.recurrente_checkbox.value)
            frecuencia = None
            if es_recurrente and self.frecuencia_dropdown.value:
                try:
                    frecuencia = RecurrenceFrequency[
                        self.frecuencia_dropdown.value
                    ]
                except KeyError:
                    pass

            income = Income(
                id=self.editing_income_id,
                family_member_id=int(self.member_dropdown.value),
                monto=monto,
                fecha=fecha,
                descripcion=self.descripcion_input.value,
                categoria=categoria,
                es_recurrente=es_recurrente,
                frecuencia=frecuencia,
                notas=self.notas_input.value if self.notas_input.value else None,
            )
            
            if self.editing_income_id:
                result = self.income_controller.update_income(income)
                success_msg = "Ingreso actualizado correctamente"
            else:
                result = self.income_controller.add_income(income)
                success_msg = "Ingreso guardado correctamente"
            
            match result:
                case Ok(_):
                    self.editing_income_id = None
                    self._clear_inputs()
                    self._render_incomes()
                    self._render_summary()
                    self._show_success(success_msg)
                
                case Err(error):
                    self._show_error(error)
        
        except Exception as e:
            self._show_error(AppError(message=f"Error inesperado: {e}"))

    def _render_incomes(self) -> None:
        """Renderizar ingresos del mes: recurrentes siempre + no-recurrentes del mes."""
        self.incomes_column.controls.clear()
        today = date.today()
        incomes = self.income_controller.list_for_month(today.year, today.month)
        
        if not incomes:
            self.incomes_column.controls.append(
                ft.Text(value="No hay ingresos registrados", italic=True)
            )
        else:
            # Ordenar por fecha descendente
            incomes_sorted = sorted(incomes, key=lambda x: x.fecha, reverse=True)
            
            for income in incomes_sorted:
                # Buscar nombre del miembro
                member_name = "Desconocido"
                for member in self.active_members:
                    if member.id == income.family_member_id:
                        member_name = member.nombre
                        break
                
                monto_formateado = format_currency(income.monto)
                recurrente_badge = (
                    ft.Container(
                        content=ft.Text(
                            "↺ Recurrente",
                            size=10,
                            color=ft.Colors.WHITE,
                            weight=ft.FontWeight.BOLD,
                        ),
                        bgcolor=ft.Colors.TEAL_600,
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    )
                    if income.es_recurrente
                    else ft.Container()
                )

                self.incomes_column.controls.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Icon(
                                    icon=ft.Icons.ACCOUNT_BALANCE_WALLET,
                                    color=ft.Colors.TEAL_600,
                                    size=30
                                ),
                                ft.Column(
                                    controls=[
                                        ft.Row(
                                            controls=[
                                                ft.Text(
                                                    value=(
                                                        f"{member_name}"
                                                        f" - {income.descripcion}"
                                                    ),
                                                    weight=ft.FontWeight.BOLD,
                                                    color=ft.Colors.TEAL_900,
                                                    expand=True,
                                                ),
                                                recurrente_badge,
                                            ],
                                            spacing=8,
                                        ),
                                        ft.Text(
                                            value=(
                                                f"{income.categoria.value} • "
                                                f"${monto_formateado} • "
                                                f"{income.fecha}"
                                            ),
                                            size=12,
                                            color=ft.Colors.TEAL_700
                                        ),
                                    ],
                                    spacing=2,
                                    expand=True
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.EDIT,
                                    tooltip="Editar",
                                    icon_color=ft.Colors.TEAL_400,
                                    on_click=(
                                        lambda e, inc=income: self._on_edit_income(inc)
                                    )
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE,
                                    tooltip="Eliminar",
                                    icon_color=ft.Colors.RED_400,
                                    on_click=lambda e, inc=income: (
                                        self._on_delete_income(inc)
                                    )
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.START
                        ),
                        padding=15,
                        bgcolor=ft.Colors.CYAN_50,
                        border=ft.border.all(2, ft.Colors.TEAL_200),
                        border_radius=10,
                        shadow=ft.BoxShadow(
                            spread_radius=1,
                            blur_radius=4,
                            color=ft.Colors.TEAL_100,
                        )
                    )
                )
        
        self.page.update()

    def _render_summary(self) -> None:
        """Renderizar resumen por categorías del mes (recurrentes + no-recurrentes)."""
        self.summary_column.controls.clear()
        today = date.today()
        summary = self.income_controller.get_summary_by_categories(
            year=today.year, month=today.month
        )
        
        if not summary:
            self.summary_column.controls.append(
                ft.Text(value="No hay datos para mostrar", italic=True)
            )
        else:
            total = sum(summary.values())
            
            # Formatear total con separador de miles
            total_formateado = format_currency(total)
            
            # Agregar total general
            self.summary_column.controls.append(
                ft.Text(
                    value=f"💰 Total de ingresos: ${total_formateado}",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.GREEN
                )
            )
            
            self.summary_column.controls.append(ft.Divider())
            
            # Ordenar por monto descendente
            sorted_summary = sorted(summary.items(), key=lambda x: x[1], reverse=True)
            
            for categoria, monto in sorted_summary:
                porcentaje = (monto / total * 100) if total > 0 else 0
                
                # Formatear monto con separador de miles
                monto_formateado = format_currency(monto)
                
                self.summary_column.controls.append(
                    ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        value=categoria,
                                        weight=ft.FontWeight.BOLD,
                                        expand=True
                                    ),
                                    ft.Text(
                                        value=(
                                            f"${monto_formateado} "
                                            f"({porcentaje:.1f}%)"
                                        )
                                    ),
                                ],
                            ),
                            ft.ProgressBar(
                                value=porcentaje / 100,
                                color=ft.Colors.GREEN,
                                bgcolor=ft.Colors.GREEN_100
                            ),
                        ],
                        spacing=5
                    )
                )
        
        self.page.update()

    def _on_edit_income(self, income: Income) -> None:
        """Cargar datos del ingreso para editar"""
        self.editing_income_id = income.id
        self.member_dropdown.value = str(income.family_member_id)
        self.monto_input.value = str(income.monto)
        self.descripcion_input.value = income.descripcion
        self.categoria_dropdown.value = income.categoria.name
        self.fecha_input.value = str(income.fecha)
        self.notas_input.value = income.notas if income.notas else ""
        self.recurrente_checkbox.value = income.es_recurrente
        self.frecuencia_dropdown.visible = income.es_recurrente
        self.frecuencia_dropdown.value = (
            income.frecuencia.name if income.frecuencia else None
        )
        self.page.update()

    def _on_delete_income(self, income: Income) -> None:
        """Eliminar un ingreso"""
        if income.id:
            result = self.income_controller.delete_income(income.id)
            match result:
                case Ok(_):
                    self._render_incomes()
                    self._render_summary()
                    self._show_success("Ingreso eliminado correctamente")
                case Err(error):
                    self._show_error(error)

    def _on_cancel_edit(self, _: ft.ControlEvent) -> None:
        """Cancelar edición"""
        self.editing_income_id = None
        self._clear_inputs()
        self.page.update()

    def _clear_inputs(self) -> None:
        """Limpiar formulario"""
        self.member_dropdown.value = None
        self.monto_input.value = ""
        self.descripcion_input.value = ""
        self.categoria_dropdown.value = None
        self.fecha_input.value = str(date.today())
        self.notas_input.value = ""
        self.recurrente_checkbox.value = False
        self.frecuencia_dropdown.value = None
        self.frecuencia_dropdown.visible = False

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
