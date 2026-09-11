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
from controllers.household_controller import HouseholdController
from controllers.installment_controller import InstallmentController
from core.session import SessionManager
from core.state import AppState
from flet_types.flet_types import CorrectElevatedButton, CorrectSnackBar
from models.categories import (
    ExpenseCategory,
    PaymentMethod,
    get_categories_for_entorno,
    get_subcategories,
)
from models.errors import AppError, ValidationError
from models.expense_model import Expense
from services.infrastructure.formatters import format_pesos
from views.components.date_picker_manager import DatePickerManager
from views.components.month_selector import MonthSelector
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
        self.household_controller = HouseholdController(familia_id=familia_id)

        # Toggle para compartir
        self.share_household_switch = ft.Switch(
            label="Compartir gasto con el hogar",
            value=False,
            active_color=ft.Colors.GREEN_600,
            active_track_color=ft.Colors.GREEN_200,
            inactive_thumb_color=ft.Colors.ORANGE_400,
            inactive_track_color=ft.Colors.ORANGE_100,
            visible=False,
        )

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

        self.entorno = SessionManager.get_active_entorno(page)
        default_currency = "USD" if self.entorno == "campo" else "UYU"

        self.currency_dropdown = ft.Dropdown(
            label="Moneda",
            expand=True,
            value=default_currency,
            options=[
                ft.dropdown.Option("UYU", "Pesos Uruguayos ($)"),
                ft.dropdown.Option("USD", "Dólares (USD)"),
            ],
        )

        categories = get_categories_for_entorno(self.entorno)
        self.categoria_dropdown = ft.Dropdown(
            label="Categoría",
            expand=True,
            options=[ft.dropdown.Option(cat.value) for cat in categories],
            on_select=self._on_categoria_changed,
        )

        self.subcategoria_dropdown = ft.Dropdown(
            label="Subcategoría (opcional)",
            expand=True,
            options=[],
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
            label="Fecha (YYYY-MM-DD)",
            value=date.today().strftime("%Y-%m-%d"),
            expand=True,
            suffix=ft.IconButton(
                icon=ft.Icons.CALENDAR_MONTH,
                tooltip="Elegir fecha en calendario",
                on_click=self._open_date_picker,
            ),
        )

        # Navegador de meses y buscador en tiempo real
        self.month_selector = MonthSelector(
            page=self.page,
            on_change=self._on_month_changed,
        )
        self.search_input = ft.TextField(
            hint_text="🔍 Buscar gasto por descripción o categoría...",
            expand=True,
            dense=True,
            on_change=self._on_search_changed,
        )
        self.expenses_count_label = ft.Text("", size=13, color=ft.Colors.BLUE_GREY_600)

        # Lista de gastos
        self.expenses_column = ft.Column(spacing=10)

        # Resumen por categorías
        self.summary_column = ft.Column(spacing=5)

    def _open_date_picker(self, _: ft.ControlEvent) -> None:
        try:
            curr_date = date.fromisoformat(self.fecha_picker.value)
        except Exception:
            curr_date = date.today()
        DatePickerManager.open_date_picker(self.page, curr_date, self._on_date_selected)

    def _on_date_selected(self, selected: date) -> None:
        self.fecha_picker.value = selected.strftime("%Y-%m-%d")
        self.page.update()

    def _on_month_changed(self, year: int, month: int) -> None:
        self._render_expenses()
        self._render_summary()

    def _on_search_changed(self, _: ft.ControlEvent) -> None:
        self._render_expenses()

    def _on_categoria_changed(self, _: ft.ControlEvent) -> None:
        """Actualizar opciones del dropdown de subcategorías al elegir categoría."""
        self._update_subcategories()
        self.page.update()

    def _update_subcategories(self, selected_subcat: str | None = None) -> None:
        """Poblar opciones de subcategoría según la categoría elegida."""
        cat_val = self.categoria_dropdown.value
        subcats = get_subcategories(cat_val) if cat_val else []
        self.subcategoria_dropdown.options = [
            ft.dropdown.Option(sub) for sub in subcats
        ]
        if selected_subcat and selected_subcat in subcats:
            self.subcategoria_dropdown.value = selected_subcat
        else:
            self.subcategoria_dropdown.value = None

    def render(self):
        """Renderizar la vista completa"""
        is_mobile = AppState.device == "mobile"

        # Validar membresía para habilitar/deshabilitar el toggle
        household_res = self.household_controller.get_current_household()
        if household_res.is_ok():
            household = household_res.unwrap()
            if household is not None:
                self.share_household_switch.visible = True
                self.share_household_switch.label = f"Compartir con: {household.nombre}"
            else:
                self.share_household_switch.visible = False
                self.share_household_switch.value = False
        else:
            self.share_household_switch.visible = False
            self.share_household_switch.value = False

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
                                        content=self.subcategoria_dropdown,
                                        col=Responsive.COL_HALF,
                                    ),
                                ],
                                spacing=10,
                                run_spacing=10,
                            ),
                            ft.ResponsiveRow(
                                controls=[
                                    ft.Container(
                                        content=self.metodo_pago_dropdown,
                                        col=Responsive.COL_HALF,
                                    ),
                                    ft.Container(
                                        content=self.currency_dropdown,
                                        col=Responsive.COL_HALF,
                                    ),
                                ],
                                spacing=10,
                                run_spacing=10,
                            ),
                            ft.Container(height=10),
                            self.share_household_switch,
                            ft.Container(height=10),
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
                # Navegador temporal mensual
                self.month_selector,
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
                ft.Row(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Text(
                                    value="📋 Gastos registrados",
                                    size=16 if is_mobile else 20,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                self.expenses_count_label,
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=8,
                        ),
                        ft.OutlinedButton(
                            "Exportar CSV",
                            icon=ft.Icons.DOWNLOAD,
                            on_click=self._on_export_csv,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self.search_input,
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
            "Enero",
            "Febrero",
            "Marzo",
            "Abril",
            "Mayo",
            "Junio",
            "Julio",
            "Agosto",
            "Setiembre",
            "Octubre",
            "Noviembre",
            "Diciembre",
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
                int(self.cuotas_dropdown.value) if self.cuotas_dropdown.value else 1
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
            self.metodo_pago_dropdown.value == PaymentMethod.TARJETA_CREDITO.value
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

            # Obtener fecha seleccionada o defecto a hoy
            try:
                fecha_gasto = date.fromisoformat(self.fecha_picker.value)
            except Exception:
                fecha_gasto = date.today()

            # Crear o actualizar el gasto
            expense = Expense(
                id=self.editing_expense_id,
                monto=Decimal(self.monto_input.value),
                currency=self.currency_dropdown.value or "UYU",
                fecha=fecha_gasto,
                descripcion=self.descripcion_input.value,
                categoria=selected_cat,
                subcategoria=self.subcategoria_dropdown.value or None,
                metodo_pago=selected_metodo,
                es_recurrente=False,
                frecuencia=None,
                notas=None,
                entorno=self.entorno,
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
                    # Si el gasto pertenece a otro mes, sincronizar el selector
                    if (
                        expense_ok.fecha.year != self.month_selector.year
                        or expense_ok.fecha.month != self.month_selector.month
                    ):
                        self.month_selector.set_period(
                            expense_ok.fecha.year, expense_ok.fecha.month, notify=False
                        )
                    # Compartir con el hogar si corresponde
                    if (
                        self.share_household_switch.visible
                        and self.share_household_switch.value
                    ):
                        share_res = self.household_controller.share_expense(
                            expense_ok.id
                        )
                        if share_res.is_err():
                            self.page.overlay.append(
                                ft.SnackBar(
                                    ft.Text(
                                        f"Gasto guardado, pero no se pudo compartir: "
                                        f"{share_res.unwrap_err()}"
                                    ),
                                    open=True,
                                    bgcolor=ft.Colors.RED_600,
                                )
                            )
                            self.page.update()

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
                                monto_cuota = Decimal(self.monto_cuota_input.value)
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
                            cuota_fmt = format_pesos(
                                installment.monto_por_cuota,
                                currency=installment.currency,
                            )
                            mensaje_exito += (
                                f" (en {installment.numero_cuotas} cuotas "
                                f"de {cuota_fmt} "
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
        """Renderizar lista de gastos del mes seleccionado con filtro de búsqueda"""
        self.expenses_column.controls.clear()
        expenses = self.controller.list_expenses_by_month(
            self.month_selector.year,
            self.month_selector.month,
            entorno=self.entorno,
        )

        # Filtro de búsqueda en tiempo real
        query = (self.search_input.value or "").strip().lower()
        if query:
            filtered = [
                exp
                for exp in expenses
                if query in exp.descripcion.lower()
                or query in exp.categoria.value.lower()
                or (exp.subcategoria and query in exp.subcategoria.lower())
            ]
            self.expenses_count_label.value = (
                f"{len(filtered)} de {len(expenses)} gastos"
            )
        else:
            filtered = expenses
            self.expenses_count_label.value = (
                f"{len(expenses)} gastos" if expenses else ""
            )

        if not filtered:
            msg = (
                f"No se encontraron gastos para '{query}'"
                if query
                else "No hay gastos registrados en este mes"
            )
            self.expenses_column.controls.append(ft.Text(value=msg, italic=True))
        else:
            for expense in reversed(filtered):  # Más recientes primero
                subcat_part = (
                    f" • {expense.subcategoria}" if expense.subcategoria else ""
                )
                self.expenses_column.controls.append(
                    ft.Container(
                        content=ft.ResponsiveRow(
                            controls=[
                                ft.Container(
                                    content=ft.Icon(
                                        icon=ft.Icons.ATTACH_MONEY,
                                        color=ft.Colors.GREEN,
                                    ),
                                    bgcolor="#ECFDF5",
                                    padding=8,
                                    border_radius=8,
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
                                                f"{expense.categoria.value}"
                                                f"{subcat_part} • "
                                                f"{expense.metodo_pago.value}"
                                            ),
                                            size=12,
                                            color=ft.Colors.GREY_700,
                                        ),
                                    ],
                                    col={"xs": 7, "sm": 4},
                                    spacing=2,
                                ),
                                ft.Container(
                                    content=ft.Text(
                                        value=format_pesos(
                                            expense.monto, currency=expense.currency
                                        ),
                                        size=18,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.RED_700,
                                        no_wrap=True,
                                        text_align=ft.TextAlign.RIGHT,
                                    ),
                                    col={"xs": 4, "sm": 3},
                                    alignment=ft.Alignment.CENTER_RIGHT,
                                ),
                                ft.Container(
                                    content=ft.Text(
                                        value=expense.fecha.strftime("%d/%m"),
                                        size=12,
                                        color=ft.Colors.GREY_600,
                                        text_align=ft.TextAlign.RIGHT,
                                    ),
                                    col={"xs": 6, "sm": 2},
                                    alignment=ft.Alignment.CENTER_RIGHT,
                                ),
                                ft.Container(
                                    content=ft.Row(
                                        controls=[
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
                                                icon_color="#EF4444",
                                                tooltip="Eliminar gasto",
                                                on_click=lambda e, exp=expense: (
                                                    self._on_delete_expense(exp)
                                                ),
                                            ),
                                        ],
                                        alignment=ft.MainAxisAlignment.END,
                                        spacing=0,
                                    ),
                                    col={"xs": 6, "sm": 2},
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.START,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=10,
                        bgcolor="#FAF8F5",
                        border=ft.Border.all(1, "#E8E2D9"),
                        border_radius=10,
                        shadow=ft.BoxShadow(
                            spread_radius=0,
                            blur_radius=6,
                            color="#0000001F",
                        ),
                    )
                )

        self.page.update()

    def _render_summary(self) -> None:
        """Renderizar resumen por categorías del mes seleccionado."""
        self.summary_column.controls.clear()
        summary = self.controller.get_summary_by_categories(
            year=self.month_selector.year,
            month=self.month_selector.month,
            entorno=self.entorno,
        )

        if not summary:
            self.summary_column.controls.append(
                ft.Text(value="No hay datos para mostrar", italic=True)
            )
        else:
            # Agrupar por moneda
            by_currency: dict[str, dict[str, Decimal]] = {}
            for (categoria, currency), monto in summary.items():
                by_currency.setdefault(currency, {})[categoria] = monto

            for currency, cat_summary in by_currency.items():
                total = sum(cat_summary.values(), Decimal("0"))

                self.summary_column.controls.append(
                    ft.Text(
                        value=("Pesos Uruguayos" if currency == "UYU" else "Dólares"),
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_GREY_700,
                    )
                )

                for categoria, monto in sorted(
                    cat_summary.items(), key=lambda x: x[1], reverse=True
                ):
                    porcentaje = float(monto / total * 100) if total > 0 else 0.0
                    monto_fmt = format_pesos(monto, currency=currency)

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
                                    value=f"{monto_fmt} ({porcentaje:.1f}%)",
                                    col={"xs": 12, "sm": 4},
                                    no_wrap=True,
                                    text_align=ft.TextAlign.RIGHT,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.START,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        )
                    )

                # Total por moneda
                self.summary_column.controls.append(
                    ft.ResponsiveRow(
                        controls=[
                            ft.Text(
                                value=f"TOTAL {currency}",
                                weight=ft.FontWeight.BOLD,
                                col={"xs": 5, "sm": 3},
                            ),
                            ft.Text(
                                value="",
                                col={"xs": 7, "sm": 5},
                            ),
                            ft.Text(
                                value=format_pesos(total, currency=currency),
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
                self.summary_column.controls.append(ft.Divider())

        self.page.update()

    def _on_edit_expense(self, expense: Expense) -> None:
        """Cargar gasto en el formulario para editar"""
        self.editing_expense_id = expense.id

        self.descripcion_input.value = expense.descripcion
        # Formatear Decimal sin notación científica ni ceros decimales innecesarios
        # Ej: Decimal("1000") -> "1000", Decimal("1500.50") -> "1500.5"
        monto_str = f"{expense.monto:f}"
        if "." in monto_str:
            monto_str = monto_str.rstrip("0").rstrip(".")
        self.monto_input.value = monto_str
        self.fecha_picker.value = expense.fecha.strftime("%Y-%m-%d")
        self.categoria_dropdown.value = expense.categoria.value
        self._update_subcategories(selected_subcat=expense.subcategoria)
        self.metodo_pago_dropdown.value = expense.metodo_pago.value
        self.currency_dropdown.value = expense.currency
        self.page.update()

    def _on_delete_expense(self, expense: Expense) -> None:
        """Eliminar un gasto"""
        if expense.id is None:
            self._show_error(ValidationError("El gasto no tiene ID válido"))
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
        self.fecha_picker.value = date.today().strftime("%Y-%m-%d")
        self.categoria_dropdown.value = None
        self.subcategoria_dropdown.value = None
        self.subcategoria_dropdown.options = []
        self.metodo_pago_dropdown.value = PaymentMethod.EFECTIVO.value
        self.share_household_switch.value = False
        self.currency_dropdown.value = "USD" if self.entorno == "campo" else "UYU"

    def _on_export_csv(self, _: ft.ControlEvent) -> None:
        """Exporta los gastos del mes seleccionado a un archivo CSV."""
        try:
            csv_text, saved_path = self.controller.export_expenses_csv(
                year=self.month_selector.year,
                month=self.month_selector.month,
                entorno=self.entorno,
            )
            self._mostrar_modal_exportacion_csv(csv_text, saved_path)
        except Exception as e:
            self._show_error(AppError(message=f"Error al generar CSV: {e}"))

    def _mostrar_modal_exportacion_csv(
        self, csv_text: str, saved_path: str | None
    ) -> None:
        from urllib.parse import urljoin

        filename = (
            f"gastos_{self.month_selector.year}_{self.month_selector.month:02d}.csv"
        )
        periodo_str = f"{self.month_selector.year}_{self.month_selector.month:02d}"
        web_download_url = f"/exports/{filename}"

        base_page_url = getattr(self.page, "url", None) or ""
        full_download_url = (
            urljoin(base_page_url, web_download_url)
            if base_page_url
            else web_download_url
        )

        async def _descargar(_):
            try:
                await self.page.launch_url(
                    full_download_url, web_popup_window_name="_blank"
                )
                self._show_success("Descarga iniciada en tu navegador")
            except Exception as ex:
                self._show_error(
                    AppError(message=f"No se pudo iniciar la descarga: {ex}")
                )

        async def _copiar(_):
            try:
                await self.page.clipboard.set(csv_text)
                self._show_success("Datos CSV copiados al portapapeles")
            except Exception as ex:
                self._show_error(AppError(message=f"No se pudo copiar: {ex}"))

        def _cerrar(_):
            dialog.open = False
            self.page.update()

        info_guardado = (
            f"Archivo guardado en servidor: {saved_path}"
            if saved_path
            else "Listo para descargar a tu dispositivo"
        )

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.TABLE_VIEW, color=ft.Colors.GREEN_700),
                    ft.Text(
                        f"Exportar Gastos ({periodo_str})",
                        weight=ft.FontWeight.BOLD,
                    ),
                ],
                spacing=8,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "Descargá el archivo CSV para abrir en Excel o "
                            "copiá los datos directamente:",
                            size=13,
                            color=ft.Colors.GREY_800,
                        ),
                        ft.TextField(
                            value=csv_text,
                            multiline=True,
                            read_only=True,
                            dense=True,
                            min_lines=4,
                            max_lines=7,
                            text_size=11,
                        ),
                        ft.Row(
                            controls=[
                                ft.ElevatedButton(
                                    "⬇️ Descargar CSV",
                                    icon=ft.Icons.DOWNLOAD,
                                    bgcolor=ft.Colors.GREEN_700,
                                    color=ft.Colors.WHITE,
                                    url=full_download_url,
                                    on_click=_descargar,
                                ),
                                ft.OutlinedButton(
                                    "📋 Copiar datos",
                                    icon=ft.Icons.CONTENT_COPY,
                                    on_click=_copiar,
                                ),
                            ],
                            spacing=10,
                            wrap=True,
                        ),
                        ft.Text(
                            info_guardado,
                            size=11,
                            color=ft.Colors.GREY_600,
                            italic=True,
                        ),
                    ],
                    spacing=12,
                    tight=True,
                ),
                width=460,
            ),
            actions=[
                ft.TextButton("Cerrar", on_click=_cerrar),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

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
