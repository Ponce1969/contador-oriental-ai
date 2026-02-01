"""
Vista para gestión de gastos familiares
"""

from __future__ import annotations

from datetime import date

import flet as ft
from result import Err, Ok

from controllers.expense_controller import ExpenseController
from core.session import SessionManager
from flet_types.flet_types import CorrectElevatedButton, CorrectSnackBar
from models.categories import (
    ExpenseCategory,
    PaymentMethod,
    RecurrenceFrequency,
    get_subcategories,
)
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
        
        # Campos del formulario
        self.descripcion_input = ft.TextField(
            label="Descripción",
            hint_text="Ej: Compra en supermercado",
            width=300
        )
        
        self.monto_input = ft.TextField(
            label="Monto ($)",
            hint_text="0.00",
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        self.categoria_dropdown = ft.Dropdown(
            label="Categoría",
            width=200,
            options=[
                ft.dropdown.Option(cat.value) for cat in ExpenseCategory
            ]
        )
        self.categoria_dropdown.on_change = self._on_category_change  # type: ignore
        
        self.subcategoria_dropdown = ft.Dropdown(
            label="Subcategoría",
            width=200,
            disabled=True
        )
        
        self.metodo_pago_dropdown = ft.Dropdown(
            label="Método de pago",
            width=200,
            value=PaymentMethod.EFECTIVO.value,
            options=[
                ft.dropdown.Option(metodo.value) for metodo in PaymentMethod
            ]
        )
        
        self.fecha_picker = ft.TextField(
            label="Fecha",
            value=date.today().strftime("%Y-%m-%d"),
            width=150,
            read_only=True
        )
        
        self.es_recurrente_checkbox = ft.Checkbox(
            label="Gasto recurrente",
            value=False
        )
        self.es_recurrente_checkbox.on_change = self._on_recurrente_change
        
        self.frecuencia_dropdown = ft.Dropdown(
            label="Frecuencia",
            width=150,
            disabled=True,
            options=[
                ft.dropdown.Option(freq.value) for freq in RecurrenceFrequency
            ]
        )
        
        self.notas_input = ft.TextField(
            label="Notas (opcional)",
            multiline=True,
            min_lines=2,
            max_lines=3,
            width=600
        )
        
        # Lista de gastos
        self.expenses_column = ft.Column(spacing=10)
        
        # Resumen por categorías
        self.summary_column = ft.Column(spacing=5)

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
                                value="� Registrar gasto",
                                size=20,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.ORANGE_700
                            ),
                            ft.Row(
                                controls=[
                                    self.descripcion_input,
                                    self.monto_input,
                                    self.fecha_picker,
                                ],
                                spacing=10
                            ),
                            ft.Row(
                                controls=[
                                    self.categoria_dropdown,
                                    self.subcategoria_dropdown,
                                    self.metodo_pago_dropdown,
                                ],
                                spacing=10
                            ),
                            ft.Row(
                                controls=[
                                    self.es_recurrente_checkbox,
                                    self.frecuencia_dropdown,
                                ],
                                spacing=10
                            ),
                            self.notas_input,
                            CorrectElevatedButton(
                                "💾 Guardar gasto",
                                on_click=self._on_add_expense
                            ),
                        ],
                        spacing=15
                    ),
                    padding=20,
                    bgcolor=ft.Colors.ORANGE_50,
                    border=ft.border.all(2, ft.Colors.ORANGE_200),
                    border_radius=10,
                    shadow=ft.BoxShadow(
                        spread_radius=1,
                        blur_radius=6,
                        color=ft.Colors.ORANGE_100,
                    )
                ),
                
                ft.Divider(),
                
                # Resumen por categorías
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(value="📊 Resumen por categorías", size=20),
                            self.summary_column,
                        ],
                        spacing=10
                    ),
                    padding=20,
                    bgcolor=ft.Colors.ORANGE_50,
                    border=ft.border.all(2, ft.Colors.ORANGE_200),
                    border_radius=10,
                    shadow=ft.BoxShadow(
                        spread_radius=1,
                        blur_radius=6,
                        color=ft.Colors.ORANGE_100,
                    )
                ),
                
                ft.Divider(),
                
                # Lista de gastos
                ft.Text(value="📋 Gastos registrados", size=20),
                self.expenses_column,
            ],
            spacing=20,
            scroll=ft.ScrollMode.AUTO
        )
        
        # Cargar datos iniciales
        self._render_expenses()
        self._render_summary()
        
        return MainLayout(
            page=self.page,
            content=content,
            router=self.router,
        )

    def _on_category_change(self, e):
        """Manejar cambio de categoría"""
        if not self.categoria_dropdown.value:
            self.subcategoria_dropdown.disabled = True
            self.subcategoria_dropdown.options = []
        else:
            # Buscar la categoría seleccionada
            selected_cat = None
            for cat in ExpenseCategory:
                if cat.value == self.categoria_dropdown.value:
                    selected_cat = cat
                    break
            
            if selected_cat:
                subcats = get_subcategories(selected_cat)
                self.subcategoria_dropdown.options = [
                    ft.dropdown.Option(subcat) for subcat in subcats
                ]
                self.subcategoria_dropdown.disabled = False
        
        self.page.update()

    def _on_recurrente_change(self, e):
        """Manejar cambio de gasto recurrente"""
        self.frecuencia_dropdown.disabled = not self.es_recurrente_checkbox.value
        self.page.update()

    def _on_add_expense(self, _: ft.ControlEvent) -> None:
        """Agregar un nuevo gasto"""
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
            
            # Buscar frecuencia si es recurrente
            selected_freq = None
            if self.es_recurrente_checkbox.value and self.frecuencia_dropdown.value:
                for freq in RecurrenceFrequency:
                    if freq.value == self.frecuencia_dropdown.value:
                        selected_freq = freq
                        break
            
            # Crear el gasto
            expense = Expense(
                descripcion=self.descripcion_input.value,
                monto=float(self.monto_input.value),
                fecha=date.today(),
                categoria=selected_cat,
                subcategoria=self.subcategoria_dropdown.value,
                metodo_pago=selected_metodo,
                es_recurrente=self.es_recurrente_checkbox.value or False,
                frecuencia_recurrencia=selected_freq,
                notas=self.notas_input.value if self.notas_input.value else None,
            )
            
            result = self.controller.add_expense(expense)
            
            match result:
                case Ok(_):
                    self._clear_inputs()
                    self._render_expenses()
                    self._render_summary()
                    self._show_success("Gasto guardado correctamente")
                
                case Err(error):
                    self._show_error(error)
        
        except ValueError:
            self._show_error(AppError(message="El monto debe ser un número válido"))

    def _render_expenses(self) -> None:
        """Renderizar lista de gastos"""
        self.expenses_column.controls.clear()
        
        expenses = self.controller.list_expenses()
        
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
        """Renderizar resumen por categorías"""
        self.summary_column.controls.clear()
        
        summary = self.controller.get_summary_by_categories()
        
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

    def _clear_inputs(self) -> None:
        """Limpiar formulario"""
        self.descripcion_input.value = ""
        self.monto_input.value = ""
        self.categoria_dropdown.value = None
        self.subcategoria_dropdown.value = None
        self.subcategoria_dropdown.disabled = True
        self.metodo_pago_dropdown.value = PaymentMethod.EFECTIVO.value
        self.es_recurrente_checkbox.value = False
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
