"""
Vista para gestión de ingresos familiares
"""

from __future__ import annotations

from datetime import date

import flet as ft
from result import Err, Ok

from controllers.family_member_controller import FamilyMemberController
from controllers.income_controller import IncomeController
from flet_types.flet_types import CorrectElevatedButton, CorrectSnackBar
from models.errors import AppError
from models.income_model import Income, IncomeCategory, RecurrenceFrequency
from views.layouts.main_layout import MainLayout


class IncomesView:
    """Vista para registrar ingresos familiares"""
    
    def __init__(self, page, router):
        self.page = page
        self.router = router
        
        # Controllers
        self.income_controller = IncomeController()
        self.member_controller = FamilyMemberController()
        
        # Cargar miembros activos
        self.active_members = self.member_controller.list_active_members()
        
        # Campos del formulario
        self.member_dropdown = ft.Dropdown(
            label="Miembro de la familia",
            width=250,
            options=[
                ft.dropdown.Option(key=str(member.id), text=member.nombre)
                for member in self.active_members
            ]
        )
        
        self.monto_input = ft.TextField(
            label="Monto ($)",
            hint_text="Ej: 50.000 o 50000",
            width=200
        )
        
        self.descripcion_input = ft.TextField(
            label="Descripción",
            hint_text="Ej: Jornal día 15, Cobro de sueldo enero",
            width=400
        )
        
        self.categoria_dropdown = ft.Dropdown(
            label="Categoría",
            width=200,
            options=[
                ft.dropdown.Option(key=cat.name, text=cat.value)
                for cat in IncomeCategory
            ]
        )
        
        self.fecha_input = ft.TextField(
            label="Fecha (YYYY-MM-DD)",
            hint_text=str(date.today()),
            value=str(date.today()),
            width=150
        )
        
        self.recurrente_checkbox = ft.Checkbox(
            label="Es recurrente",
            value=False
        )
        
        self.frecuencia_dropdown = ft.Dropdown(
            label="Frecuencia",
            width=150,
            disabled=True,
            options=[
                ft.dropdown.Option(key=freq.name, text=freq.value)
                for freq in RecurrenceFrequency
            ]
        )
        
        self.notas_input = ft.TextField(
            label="Notas (opcional)",
            multiline=True,
            min_lines=2,
            max_lines=3,
            width=600
        )
        
        # Lista de ingresos
        self.incomes_column = ft.Column(spacing=10)
        
        # Resumen
        self.summary_column = ft.Column(spacing=5)
        
        # Estado de edición
        self.editing_income_id = None

    def render(self):
        """Renderizar la vista completa"""
        content = ft.Column(
            controls=[
                ft.Text(
                    value=self.income_controller.get_title(),
                    size=28,
                    weight="bold"
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
                                size=20,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.TEAL_700
                            ),
                            ft.Row(
                                controls=[
                                    self.member_dropdown,
                                    self.categoria_dropdown,
                                    self.monto_input,
                                    self.fecha_input,
                                ],
                                spacing=10
                            ),
                            self.descripcion_input,
                            ft.Row(
                                controls=[
                                    self.recurrente_checkbox,
                                    self.frecuencia_dropdown,
                                ],
                                spacing=10
                            ),
                            self.notas_input,
                            ft.Row(
                                controls=[
                                    CorrectElevatedButton(
                                        (
                                            "💾 Guardar"
                                            if not self.editing_income_id
                                            else "✅ Actualizar"
                                        ),
                                        on_click=self._on_save_income
                                    ),
                                    CorrectElevatedButton(
                                        "❌ Cancelar",
                                        on_click=self._on_cancel_edit
                                    ) if self.editing_income_id else ft.Container(),
                                ],
                                spacing=10
                            ),
                        ],
                        spacing=15
                    ),
                    padding=20,
                    bgcolor=ft.Colors.CYAN_50,
                    border=ft.border.all(2, ft.Colors.TEAL_200),
                    border_radius=10,
                    shadow=ft.BoxShadow(
                        spread_radius=1,
                        blur_radius=6,
                        color=ft.Colors.TEAL_100,
                    )
                ),
                
                ft.Divider(),
                
                # Resumen por categorías
                ft.Text(value="📊 Resumen por categorías", size=20),
                self.summary_column,
                
                ft.Divider(),
                
                # Lista de ingresos
                ft.Text(value="💵 Ingresos registrados", size=20),
                self.incomes_column,
            ],
            spacing=20,
            scroll=ft.ScrollMode.AUTO
        )
        
        # Cargar datos iniciales
        self._render_incomes()
        self._render_summary()
        
        return MainLayout(
            page=self.page,
            content=content,
            router=self.router,
        )

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
            
            # Obtener frecuencia si es recurrente
            frecuencia = None
            if self.recurrente_checkbox.value:
                if not self.frecuencia_dropdown.value:
                    self._show_error(
                        AppError(
                            message=(
                                "Debe seleccionar frecuencia "
                                "para ingresos recurrentes"
                            )
                        )
                    )
                    return
                try:
                    frecuencia = RecurrenceFrequency[self.frecuencia_dropdown.value]
                except KeyError:
                    self._show_error(AppError(message="Frecuencia inválida"))
                    return
            
            # Crear o actualizar el ingreso
            income = Income(
                id=self.editing_income_id,
                family_member_id=int(self.member_dropdown.value),
                monto=monto,
                fecha=fecha,
                descripcion=self.descripcion_input.value,
                categoria=categoria,
                es_recurrente=self.recurrente_checkbox.value,
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
        """Renderizar lista de ingresos"""
        self.incomes_column.controls.clear()
        
        incomes = self.income_controller.list_incomes()
        
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
                
                recurrente_text = ""
                if income.es_recurrente and income.frecuencia:
                    recurrente_text = f" 🔄 {income.frecuencia.value}"
                
                # Formatear monto con separador de miles
                monto_formateado = f"{income.monto:,.0f}".replace(",", ".")
                
                self.incomes_column.controls.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Icon(
                                    ft.Icons.ACCOUNT_BALANCE_WALLET,
                                    color=ft.Colors.TEAL_600,
                                    size=30
                                ),
                                ft.Column(
                                    controls=[
                                        ft.Text(
                                            value=(
                                            f"{member_name} - {income.descripcion}"
                                        ),
                                            weight=ft.FontWeight.BOLD,
                                            color=ft.Colors.TEAL_900
                                        ),
                                        ft.Text(
                                            value=(
                                            f"{income.categoria.value} • "
                                            f"${monto_formateado} • "
                                            f"{income.fecha}{recurrente_text}"
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
        """Renderizar resumen por categorías"""
        self.summary_column.controls.clear()
        
        summary = self.income_controller.get_summary_by_categories()
        
        if not summary:
            self.summary_column.controls.append(
                ft.Text(value="No hay datos para mostrar", italic=True)
            )
        else:
            total = sum(summary.values())
            
            # Formatear total con separador de miles
            total_formateado = f"{total:,.0f}".replace(",", ".")
            
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
                monto_formateado = f"{monto:,.0f}".replace(",", ".")
                
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
        self.recurrente_checkbox.value = income.es_recurrente
        if income.frecuencia:
            self.frecuencia_dropdown.value = income.frecuencia.name
            self.frecuencia_dropdown.disabled = False
        self.notas_input.value = income.notas if income.notas else ""
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
        self.recurrente_checkbox.value = False
        self.frecuencia_dropdown.value = None
        self.frecuencia_dropdown.disabled = True
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
