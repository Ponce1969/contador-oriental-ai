"""
Vista para gestión de gastos familiares
"""

from __future__ import annotations

from datetime import date

import flet as ft
from result import Err, Ok

from constants.responsive import Responsive
from controllers.expense_controller import ExpenseController
from core.session import SessionManager
from core.state import AppState
from flet_types.flet_types import CorrectElevatedButton, CorrectSnackBar
from models.categories import ExpenseCategory, PaymentMethod
from models.errors import AppError
from models.expense_model import Expense
from views.layouts.main_layout import MainLayout


class ExpensesView:
    """Vista para registrar y visualizar gastos familiares"""
    
    def __init__(self, page, router):
        self.page = page
        self.router = router
        
        # Verificar login
        if not SessionManager.is_logged_in(page):
            router.navigate("/login")
            return
        
        # Obtener familia_id de la sesión
        familia_id = SessionManager.get_familia_id(page)
        
        # Controller con gestión automática de sesión
        self.controller = ExpenseController(familia_id=familia_id)
        
        # Estado de edición
        self.editing_expense_id = None
        
        # Campos del formulario
        self.descripcion_input = ft.TextField(
            label="Descripción",
            hint_text="Ej: Compra en supermercado",
            expand=True,
        )

        self.monto_input = ft.TextField(
            label="Monto ($)",
            hint_text="0.00",
            expand=True,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        self.categoria_dropdown = ft.Dropdown(
            label="Categoría",
            expand=True,
            options=[
                ft.dropdown.Option(cat.value) for cat in ExpenseCategory
            ],
        )

        self.metodo_pago_dropdown = ft.Dropdown(
            label="Método de pago",
            expand=True,
            value=PaymentMethod.EFECTIVO.value,
            options=[
                ft.dropdown.Option(metodo.value) for metodo in PaymentMethod
            ],
        )

        self.fecha_picker = ft.TextField(
            label="Fecha",
            value=date.today().strftime("%Y-%m-%d"),
            expand=True,
            read_only=True,
        )

        
        # Lista de gastos
        self.expenses_column = ft.Column(spacing=10)
        
        # Resumen por categorías
        self.summary_column = ft.Column(spacing=5)

    def render(self):
        """Renderizar la vista completa"""
        is_mobile = AppState.device == "mobile"

        content = ft.Column(
            controls=[
                ft.Text(
                    value=self.controller.get_title(),
                    size=20 if is_mobile else 28,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Divider(),

                # Formulario de registro
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                value="Registrar gasto",
                                size=16 if is_mobile else 20,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.ORANGE_700,
                            ),
                            ft.ResponsiveRow(
                                controls=[
                                    ft.Container(
                                        content=self.descripcion_input,
                                        col={"xs": 12, "sm": 5},
                                    ),
                                    ft.Container(
                                        content=self.monto_input,
                                        col=Responsive.COL_THIRD,
                                    ),
                                    ft.Container(
                                        content=self.fecha_picker,
                                        col=Responsive.COL_THIRD,
                                    ),
                                ],
                                spacing=10,
                                run_spacing=10,
                            ),
                            ft.ResponsiveRow(
                                controls=[
                                    ft.Container(
                                        content=self.categoria_dropdown,
                                        col=Responsive.COL_HALF,
                                    ),
                                    ft.Container(
                                        content=self.metodo_pago_dropdown,
                                        col=Responsive.COL_HALF,
                                    ),
                                ],
                                spacing=10,
                                run_spacing=10,
                            ),
                            CorrectElevatedButton(
                                "💾 Guardar gasto",
                                on_click=self._on_add_expense,
                            ),
                        ],
                        spacing=12,
                    ),
                    padding=16 if is_mobile else 20,
                    bgcolor=ft.Colors.ORANGE_50,
                    border=ft.border.all(2, ft.Colors.ORANGE_200),
                    border_radius=10,
                    shadow=ft.BoxShadow(
                        spread_radius=1,
                        blur_radius=6,
                        color=ft.Colors.ORANGE_100,
                    ),
                ),

                ft.Divider(),

                # Resumen por categorías
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                value="📊 Resumen por categorías",
                                size=16 if is_mobile else 20,
                            ),
                            self.summary_column,
                        ],
                        spacing=10,
                    ),
                    padding=16 if is_mobile else 20,
                    bgcolor=ft.Colors.ORANGE_50,
                    border=ft.border.all(2, ft.Colors.ORANGE_200),
                    border_radius=10,
                    shadow=ft.BoxShadow(
                        spread_radius=1,
                        blur_radius=6,
                        color=ft.Colors.ORANGE_100,
                    ),
                ),

                ft.Divider(),

                ft.Text(
                    value="📋 Gastos registrados",
                    size=16 if is_mobile else 20,
                ),
                self.expenses_column,
            ],
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
        )

        # Cargar datos iniciales
        self._render_expenses()
        self._render_summary()

        # FAB para escanear ticket con OCR
        self.page.floating_action_button = ft.FloatingActionButton(
            icon=ft.Icons.CAMERA_ALT_ROUNDED,
            tooltip="Escanear ticket con IA",
            bgcolor=ft.Colors.ORANGE_700,
            foreground_color=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=16),
            elevation=6,
            on_click=lambda _: self.router.navigate("/ticket-ocr"),
        )

        return MainLayout(
            page=self.page,
            content=content,
            router=self.router,
        )

    def _on_add_expense(self, _: ft.ControlEvent) -> None:
        """Agregar o actualizar un gasto"""
        try:
            # Validar campos obligatorios
            if not self.descripcion_input.value:
                self._show_error(AppError(message="La descripción es obligatoria"))
                return
            
            if not self.monto_input.value:
                self._show_error(AppError(message="El monto es obligatorio"))
                return
            
            if not self.categoria_dropdown.value:
                self._show_error(AppError(message="La categoría es obligatoria"))
                return
            
            # Buscar la categoría enum
            selected_cat = None
            for cat in ExpenseCategory:
                if cat.value == self.categoria_dropdown.value:
                    selected_cat = cat
                    break
            
            if not selected_cat:
                self._show_error(AppError(message="Categoría inválida"))
                return
            
            # Buscar método de pago enum
            selected_metodo = PaymentMethod.EFECTIVO
            for metodo in PaymentMethod:
                if metodo.value == self.metodo_pago_dropdown.value:
                    selected_metodo = metodo
                    break
            
            # Crear o actualizar el gasto
            expense = Expense(
                id=self.editing_expense_id,
                monto=float(self.monto_input.value),
                fecha=date.today(),
                descripcion=self.descripcion_input.value,
                categoria=selected_cat,
                metodo_pago=selected_metodo,
                es_recurrente=False,
                frecuencia_recurrencia=None,
                notas=None,
            )
            
            # Decidir si crear o actualizar
            if self.editing_expense_id:
                result = self.controller.update_expense(expense)
                mensaje_exito = "Gasto actualizado correctamente"
            else:
                result = self.controller.add_expense(expense)
                mensaje_exito = "Gasto guardado correctamente"
            
            match result:
                case Ok(_):
                    self._clear_inputs()
                    self._render_expenses()
                    self._render_summary()
                    self._show_success(mensaje_exito)
                
                case Err(error):
                    self._show_error(error)
        
        except ValueError:
            self._show_error(AppError(message="El monto debe ser un número válido"))

    def _render_expenses(self) -> None:
        """Renderizar lista de gastos del mes actual"""
        self.expenses_column.controls.clear()
        today = date.today()
        expenses = self.controller.list_expenses_by_month(today.year, today.month)
        
        if not expenses:
            self.expenses_column.controls.append(
                ft.Text(value="No hay gastos registrados", italic=True)
            )
        else:
            for expense in reversed(expenses):  # Más recientes primero
                self.expenses_column.controls.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Icon(
                                    icon=ft.Icons.ATTACH_MONEY,
                                    color=ft.Colors.GREEN
                                ),
                                ft.Column(
                                    controls=[
                                        ft.Text(
                                            value=expense.descripcion,
                                            weight=ft.FontWeight.BOLD
                                        ),
                                        ft.Text(
                                            value=(
                                            f"{expense.categoria.value} • "
                                            f"{expense.metodo_pago.value}"
                                        ),
                                            size=12,
                                            color=ft.Colors.GREY_700
                                        ),
                                    ],
                                    spacing=2,
                                    expand=True
                                ),
                                ft.Text(
                                    value=f"${expense.monto:.2f}",
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.RED_700
                                ),
                                ft.Text(
                                    value=expense.fecha.strftime("%d/%m"),
                                    size=12,
                                    color=ft.Colors.GREY_600
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.EDIT,
                                    icon_color=ft.Colors.BLUE,
                                    tooltip="Editar gasto",
                                    on_click=lambda e, exp=expense: self._on_edit_expense(exp)
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE,
                                    icon_color=ft.Colors.RED,
                                    tooltip="Eliminar gasto",
                                    on_click=lambda e, exp=expense: self._on_delete_expense(exp)
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        padding=10,
                        border=ft.border.all(1, ft.Colors.OUTLINE),
                        border_radius=5
                    )
                )
        
        self.page.update()

    def _render_summary(self) -> None:
        """Renderizar resumen por categorías del mes actual"""
        self.summary_column.controls.clear()
        today = date.today()
        summary = self.controller.get_summary_by_categories(
            year=today.year, month=today.month
        )
        
        if not summary:
            self.summary_column.controls.append(
                ft.Text(value="No hay datos para mostrar", italic=True)
            )
        else:
            total = sum(summary.values())
            
            for categoria, monto in sorted(
                summary.items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                porcentaje = (monto / total * 100) if total > 0 else 0
                
                self.summary_column.controls.append(
                    ft.Row(
                        controls=[
                            ft.Text(value=categoria, width=150),
                            ft.ProgressBar(
                                value=porcentaje / 100,
                                width=200,
                                color=ft.Colors.BLUE,
                                bgcolor=ft.Colors.BLUE_100
                            ),
                            ft.Text(
                                value=f"${monto:.2f} ({porcentaje:.1f}%)",
                                width=150
                            ),
                        ]
                    )
                )
            
            # Total general
            self.summary_column.controls.append(ft.Divider())
            self.summary_column.controls.append(
                ft.Row(
                    controls=[
                        ft.Text(value="TOTAL", weight=ft.FontWeight.BOLD, width=150),
                        ft.Text(value="", width=200),
                        ft.Text(
                            value=f"${total:.2f}",
                            weight=ft.FontWeight.BOLD,
                            size=18,
                            color=ft.Colors.RED_700,
                            width=150
                        ),
                    ]
                )
            )
        
        self.page.update()

    def _on_edit_expense(self, expense: Expense) -> None:
        """Cargar gasto en el formulario para editar"""
        self.editing_expense_id = expense.id
        
        self.descripcion_input.value = expense.descripcion
        self.monto_input.value = str(expense.monto)
        self.categoria_dropdown.value = expense.categoria.value
        self.metodo_pago_dropdown.value = expense.metodo_pago.value
        self.page.update()
    
    def _on_delete_expense(self, expense: Expense) -> None:
        """Eliminar un gasto"""
        if expense.id is None:
            self._show_error("El gasto no tiene ID válido")
            return
        result = self.controller.delete_expense(expense.id)
        
        match result:
            case Ok(_):
                self._render_expenses()
                self._render_summary()
                self._show_success("Gasto eliminado correctamente")
            case Err(error):
                self._show_error(error)
    
    def _clear_inputs(self) -> None:
        """Limpiar formulario"""
        self.editing_expense_id = None
        self.descripcion_input.value = ""
        self.monto_input.value = ""
        self.categoria_dropdown.value = None
        self.metodo_pago_dropdown.value = PaymentMethod.EFECTIVO.value

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
