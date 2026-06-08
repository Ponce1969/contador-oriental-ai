"""
Vista para gestión de gastos familiares
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

import flet as ft
from result import Err, Ok

from constants.responsive import Responsive
from controllers.expense_controller import ExpenseController
from controllers.installment_controller import InstallmentController
from core.session import SessionManager
from core.state import AppState
from flet_types.flet_types import CorrectElevatedButton, CorrectSnackBar
from models.categories import ExpenseCategory, PaymentMethod
from models.errors import AppError
from models.expense_model import Expense
from services.infrastructure.formatters import format_pesos
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
        self.installment_controller = InstallmentController(familia_id=familia_id)

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
            options=[ft.dropdown.Option(cat.value) for cat in ExpenseCategory],
        )

        self.metodo_pago_dropdown = ft.Dropdown(
            label="Método de pago",
            expand=True,
            value=PaymentMethod.EFECTIVO.value,
            options=[ft.dropdown.Option(metodo.value) for metodo in PaymentMethod],
        )
        self.metodo_pago_dropdown.on_select = self._on_metodo_pago_change

        # --- Campos de cuotas (ocultos por defecto) ---
        self.tarjeta_input = ft.TextField(
            label="Nombre de la tarjeta",
            hint_text="OCA, Scotia, Santander...",
            expand=True,
        )

        self.cuotas_dropdown = ft.Dropdown(
            label="Cantidad de cuotas",
            expand=True,
            options=[ft.dropdown.Option(str(i)) for i in range(2, 13)]
            + [ft.dropdown.Option(str(i)) for i in range(18, 49, 6)],
            on_select=self._on_cuotas_change,
        )

        self.monto_cuota_input = ft.TextField(
            label="Monto por cuota ($)",
            hint_text="Auto-calculado",
            expand=True,
            keyboard_type=ft.KeyboardType.NUMBER,
            read_only=True,
            on_change=self._on_monto_cuota_manual,
        )

        self.auto_calculo_switch = ft.Switch(
            label="Cálculo automático",
            value=True,
            active_color=ft.Colors.BLUE_700,
            on_change=self._on_auto_calculo_change,
        )

        self._total_financiado_label = ft.Text(
            "",
            size=12,
            color=ft.Colors.GREY_600,
            italic=True,
        )

        self.mes_inicio_dropdown = ft.Dropdown(
            label="Mes de inicio del pago",
            expand=True,
            hint_text="Según cierre de tarjeta",
            options=self._generar_meses_inicio(),
        )

        self._cuotas_container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(
                                "💳 Compra en cuotas",
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.BLUE_700,
                            ),
                            self.auto_calculo_switch,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    self._total_financiado_label,
                    ft.ResponsiveRow(
                        controls=[
                            ft.Container(
                                content=self.tarjeta_input, col={"xs": 12, "sm": 4}
                            ),
                            ft.Container(
                                content=self.cuotas_dropdown, col=Responsive.COL_THIRD
                            ),
                            ft.Container(
                                content=self.monto_cuota_input,
                                col=Responsive.COL_THIRD,
                            ),
                        ],
                        spacing=10,
                    ),
                    ft.ResponsiveRow(
                        controls=[
                            ft.Container(
                                content=self.mes_inicio_dropdown,
                                col={"xs": 12, "sm": 6},
                            ),
                        ],
                        spacing=10,
                    ),
                ],
                spacing=8,
            ),
            padding=10,
            bgcolor=ft.Colors.BLUE_50,
            border_radius=8,
            visible=False,  # Oculto hasta que se seleccione tarjeta de crédito
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
                ft.Row(
                    controls=[
                        ft.Text(
                            value=self.controller.get_title(),
                            size=20 if is_mobile else 28,
                            weight=ft.FontWeight.BOLD,
                            expand=True,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.CAMERA_ALT_ROUNDED,
                            tooltip="Escanear ticket con IA",
                            icon_color=ft.Colors.ORANGE_700,
                            icon_size=28,
                            on_click=lambda _: self.router.navigate("/ticket-ocr"),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
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
                            self._cuotas_container,
                            CorrectElevatedButton(
                                "💾 Guardar gasto",
                                on_click=self._on_add_expense,
                            ),
                        ],
                        spacing=6,
                    ),
                    padding=16 if is_mobile else 20,
                    bgcolor=ft.Colors.ORANGE_50,
                    border=ft.Border.all(2, ft.Colors.ORANGE_200),
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
                    border=ft.Border.all(2, ft.Colors.ORANGE_200),
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

        # Ocultar FAB para que no tape botones de borrar
        self.page.floating_action_button = None

        return MainLayout(
            page=self.page,
            content=content,
            router=self.router,
        )

    def _generar_meses_inicio(self) -> list[ft.dropdown.Option]:
        """Generar meses dinámicos desde el mes actual hasta 12 meses adelante"""
        meses = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre",
        ]
        hoy = date.today()
        options = []
        for i in range(12):
            mes_num = ((hoy.month - 1 + i) % 12) + 1
            año = hoy.year + ((hoy.month - 1 + i) // 12)
            fecha_str = f"{año}-{mes_num:02d}-01"
            label = f"{meses[mes_num - 1]} {año}"
            options.append(ft.dropdown.Option(fecha_str, label))
        return options

    def _on_auto_calculo_change(self, e: ft.ControlEvent) -> None:
        """Alternar entre cálculo automático y manual"""
        self.monto_cuota_input.read_only = self.auto_calculo_switch.value
        if self.auto_calculo_switch.value:
            self.monto_cuota_input.hint_text = "Auto-calculado"
            self._recalcular_auto()
        else:
            self.monto_cuota_input.hint_text = "Ingresar monto manual"
        self.monto_cuota_input.update()
        self._actualizar_total_financiado()

    def _on_monto_cuota_manual(self, e: ft.ControlEvent) -> None:
        """Cuando el usuario modifica manualmente el monto por cuota"""
        if not self.auto_calculo_switch.value:
            self._recalcular_manual()

    def _recalcular_auto(self) -> None:
        """Modo automático: total / cuotas"""
        if self.monto_input.value and self.cuotas_dropdown.value:
            try:
                from decimal import ROUND_DOWN as _RD
                total = Decimal(self.monto_input.value)
                cuotas = int(self.cuotas_dropdown.value)
                monto_cuota = (total / cuotas).quantize(Decimal("1"), rounding=_RD)
                self.monto_cuota_input.value = str(monto_cuota)
                self._actualizar_total_financiado()
            except Exception:
                pass

    def _recalcular_manual(self) -> None:
        """Modo manual: cuota * N → actualizar total"""
        if self.monto_cuota_input.value and self.cuotas_dropdown.value:
            try:
                cuota = Decimal(self.monto_cuota_input.value)
                cuotas = int(self.cuotas_dropdown.value)
                total_financiado = cuota * cuotas
                self._total_financiado_label.value = (
                    f"Total financiado: {format_pesos(total_financiado)}"
                )
            except Exception:
                pass

    def _actualizar_total_financiado(self) -> None:
        """Mostrar diferencia entre contado y financiado (si aplica)"""
        try:
            if not self.monto_input.value or not self.monto_cuota_input.value:
                self._total_financiado_label.value = ""
                return
            contado = Decimal(self.monto_input.value)
            cuotas = (
                int(self.cuotas_dropdown.value)
                if self.cuotas_dropdown.value else 1
            )
            monto_cuota = Decimal(self.monto_cuota_input.value)
            financiado = monto_cuota * cuotas
            if financiado != contado:
                interes = financiado - contado
                self._total_financiado_label.value = (
                    f"Total financiado: {format_pesos(financiado)} "
                    f"(+{format_pesos(interes)} de interés)"
                )
                self._total_financiado_label.color = ft.Colors.RED_600
            else:
                self._total_financiado_label.value = (
                    f"Total: {format_pesos(contado)} (sin interés)"
                )
                self._total_financiado_label.color = ft.Colors.GREEN_600
        except Exception:
            pass

    def _on_cuotas_change(self, e: ft.ControlEvent) -> None:
        """Auto-calcular al cambiar cuotas"""
        if self.auto_calculo_switch.value:
            self._recalcular_auto()
        else:
            self._recalcular_manual()

    def _on_metodo_pago_change(self, e: ft.ControlEvent) -> None:
        """Mostrar/ocultar campos de cuotas cuando se selecciona tarjeta de crédito"""
        is_credit = (
            self.metodo_pago_dropdown.value
            == PaymentMethod.TARJETA_CREDITO.value
        )
        self._cuotas_container.visible = is_credit
        self.page.update()

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
                monto=Decimal(self.monto_input.value),
                fecha=date.today(),
                descripcion=self.descripcion_input.value,
                categoria=selected_cat,
                metodo_pago=selected_metodo,
                es_recurrente=False,
                frecuencia=None,
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
                case Ok(expense_ok):
                    # Si es tarjeta de crédito, crear compra en cuotas
                    if (
                        selected_metodo == PaymentMethod.TARJETA_CREDITO
                        and self.tarjeta_input.value
                        and self.cuotas_dropdown.value
                    ):
                        mes_inicio = None
                        if self.mes_inicio_dropdown.value:
                            mes_inicio = date.fromisoformat(
                                self.mes_inicio_dropdown.value
                            )
                        # Monto por cuota personalizado (con recargo)
                        monto_cuota = None
                        if (
                            self.monto_cuota_input.value
                            and self.monto_cuota_input.value != ""
                        ):
                            try:
                                monto_cuota = Decimal(
                                    self.monto_cuota_input.value
                                )
                            except (ValueError, InvalidOperation):
                                pass
                        installment_result = (
                            self.installment_controller.crear_compra_cuotas(
                                expense=expense_ok,
                                nombre_tarjeta=self.tarjeta_input.value,
                                numero_cuotas=int(self.cuotas_dropdown.value),
                                mes_inicio_pago=mes_inicio,
                                monto_por_cuota=monto_cuota,
                            )
                        )
                        if isinstance(installment_result, Ok):
                            installment = installment_result.ok()
                            mensaje_exito += (
                                f" (en {installment.numero_cuotas} cuotas "
                                f"de {format_pesos(installment.monto_por_cuota)} "
                                f"con {installment.nombre_tarjeta})"
                            )

                    self._clear_inputs()
                    self._render_expenses()
                    self._render_summary()
                    self._show_success(mensaje_exito)

                case Err(error):
                    self._show_error(error)

        except (ValueError, InvalidOperation):
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
                        content=ft.ResponsiveRow(
                            controls=[
                                ft.Container(
                                    content=ft.Icon(
                                        icon=ft.Icons.ATTACH_MONEY,
                                        color=ft.Colors.GREEN,
                                    ),
                                    col={"xs": 1, "sm": 1},
                                    alignment=ft.Alignment.CENTER_LEFT,
                                ),
                                ft.Column(
                                    controls=[
                                        ft.Text(
                                            value=expense.descripcion,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        ft.Text(
                                            value=(
                                                f"{expense.categoria.value} • "
                                                f"{expense.metodo_pago.value}"
                                            ),
                                            size=12,
                                            color=ft.Colors.GREY_700,
                                        ),
                                    ],
                                    col={"xs": 5, "sm": 5},
                                    spacing=2,
                                ),
                                ft.Container(
                                    content=ft.Text(
                                        value=format_pesos(expense.monto),
                                        size=18,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.RED_700,
                                        no_wrap=True,
                                        text_align=ft.TextAlign.RIGHT,
                                    ),
                                    col={"xs": 3, "sm": 2},
                                    alignment=ft.Alignment.CENTER_RIGHT,
                                ),
                                ft.Container(
                                    content=ft.Row(
                                        controls=[
                                            ft.Text(
                                                value=expense.fecha.strftime("%d/%m"),
                                                size=12,
                                                color=ft.Colors.GREY_600,
                                            ),
                                            ft.IconButton(
                                                icon=ft.Icons.EDIT,
                                                icon_color=ft.Colors.BLUE,
                                                tooltip="Editar gasto",
                                                on_click=lambda e, exp=expense: (
                                                    self._on_edit_expense(exp)
                                                ),
                                            ),
                                            ft.IconButton(
                                                icon=ft.Icons.DELETE,
                                                icon_color=ft.Colors.RED,
                                                tooltip="Eliminar gasto",
                                                on_click=lambda e, exp=expense: (
                                                    self._on_delete_expense(exp)
                                                ),
                                            ),
                                        ],
                                        spacing=0,
                                        alignment=ft.MainAxisAlignment.END,
                                    ),
                                    col={"xs": 3, "sm": 4},
                                    alignment=ft.Alignment.CENTER_RIGHT,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.START,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=10,
                        border=ft.Border.all(1, ft.Colors.OUTLINE),
                        border_radius=5,
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
            total = sum(summary.values(), Decimal("0"))

            for categoria, monto in sorted(
                summary.items(), key=lambda x: x[1], reverse=True
            ):
                porcentaje = float((monto / total * 100)) if total > 0 else 0.0

                self.summary_column.controls.append(
                    ft.ResponsiveRow(
                        controls=[
                            ft.Text(
                                value=categoria,
                                col={"xs": 5, "sm": 3},
                                no_wrap=True,
                            ),
                            ft.ProgressBar(
                                value=porcentaje / 100,
                                col={"xs": 7, "sm": 5},
                                color=ft.Colors.BLUE,
                                bgcolor=ft.Colors.BLUE_100,
                            ),
                            ft.Text(
                                value=f"{format_pesos(monto)} ({porcentaje:.1f}%)",
                                col={"xs": 12, "sm": 4},
                                no_wrap=True,
                                text_align=ft.TextAlign.RIGHT,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                )

            # Total general
            self.summary_column.controls.append(ft.Divider())
            self.summary_column.controls.append(
                ft.ResponsiveRow(
                    controls=[
                        ft.Text(
                            value="TOTAL",
                            weight=ft.FontWeight.BOLD,
                            col={"xs": 5, "sm": 3},
                        ),
                        ft.Text(
                            value="",
                            col={"xs": 7, "sm": 5},
                        ),
                        ft.Text(
                            value=format_pesos(total),
                            weight=ft.FontWeight.BOLD,
                            size=18,
                            color=ft.Colors.RED_700,
                            col={"xs": 12, "sm": 4},
                            no_wrap=True,
                            text_align=ft.TextAlign.RIGHT,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )

        self.page.update()

    def _on_edit_expense(self, expense: Expense) -> None:
        """Cargar gasto en el formulario para editar"""
        self.editing_expense_id = expense.id

        self.descripcion_input.value = expense.descripcion
        self.monto_input.value = str(expense.monto).rstrip("0").rstrip(".")
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
            content=ft.Text(value=f"❌ {error.message}"), open=True
        )
        self.page.overlay.append(snack_bar)
        self.page.update()

    def _show_success(self, message: str) -> None:
        """Mostrar mensaje de éxito"""
        snack_bar = CorrectSnackBar(content=ft.Text(value=f"✅ {message}"), open=True)
        self.page.overlay.append(snack_bar)
        self.page.update()
