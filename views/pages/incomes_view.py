"""
Vista para gestión de ingresos familiares
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import flet as ft
from result import Err, Ok

from constants.responsive import Responsive
from controllers.family_member_controller import FamilyMemberController
from controllers.income_controller import IncomeController
from controllers.labor_controller import LaborController, parse_decimal
from core.session import SessionManager
from core.state import AppState
from flet_types.flet_types import CorrectElevatedButton, CorrectSnackBar
from models.errors import AppError
from models.income_model import Income, IncomeCategory, RecurrenceFrequency
from services.labor.domain.enums import ActivityNature
from services.labor.domain.models import EconomicActivity
from services.labor.engine import LaborCalculationEngine
from utils.formatters import format_currency, format_currency_with_symbol
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
        self.labor_controller = LaborController(familia_id=familia_id)

        # Estado de actividad económica vinculada
        self.selected_economic_activity_id: int | None = None
        self.labor_suggestion_container = ft.Container(visible=False)

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
            on_select=self._on_member_selected,
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

        self.concept_dropdown = ft.Dropdown(
            label="Concepto Laboral / Legal",
            expand=True,
            value="salary",
            options=[
                ft.dropdown.Option("salary", "💼 Sueldo mensual habitual / Jornal"),
                ft.dropdown.Option("aguinaldo", "🎁 Aguinaldo cobrado (SAC)"),
                ft.dropdown.Option("vacation_pay", "🏖️ Salario Vacacional cobrado"),
                ft.dropdown.Option("overtime", "⏱️ Horas extras (computable)"),
                ft.dropdown.Option("commission", "📈 Comisiones (computable)"),
                ft.dropdown.Option("bonus", "💰 Bono / Extra"),
                ft.dropdown.Option("other", "💵 Otro ingreso"),
            ],
        )

        self.currency_dropdown = ft.Dropdown(
            label="Moneda",
            expand=True,
            value="UYU",
            options=[
                ft.dropdown.Option("UYU", "Pesos Uruguayos ($)"),
                ft.dropdown.Option("USD", "Dólares (USD)"),
            ],
        )

        self.fecha_input = ft.TextField(
            label="Fecha (YYYY-MM-DD)",
            hint_text=str(date.today()),
            value=str(date.today()),
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

        # Controles dinámicos del formulario
        self.form_title = ft.Text(
            value="💰 Registrar ingreso",
            size=20,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.TEAL_700,
        )
        self.save_button = CorrectElevatedButton(
            "💾 Guardar",
            on_click=self._on_save_income,
        )
        self.cancel_button = CorrectElevatedButton(
            "❌ Cancelar",
            on_click=self._on_cancel_edit,
            visible=False,
        )

    def render(self):
        """Renderizar la vista completa"""
        is_mobile = AppState.device == "mobile"
        self.form_title.size = 16 if is_mobile else 20

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
                            self.form_title,
                            self.labor_suggestion_container,
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
                                        content=self.concept_dropdown,
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
                                    ft.Container(
                                        content=self.currency_dropdown,
                                        col=Responsive.COL_HALF,
                                    ),
                                ],
                                spacing=10,
                                run_spacing=10,
                            ),
                            self.descripcion_input,
                            self.recurrente_checkbox,
                            self.frecuencia_dropdown,
                            ft.Row(
                                controls=[
                                    self.save_button,
                                    self.cancel_button,
                                ],
                                spacing=10,
                            ),
                        ],
                        spacing=12,
                    ),
                    padding=16 if is_mobile else 20,
                    bgcolor=ft.Colors.CYAN_50,
                    border=ft.Border.all(2, ft.Colors.TEAL_200),
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

    def _on_member_selected(self, _: Any) -> None:
        """Detecta si el miembro tiene una actividad laboral y sugiere datos."""
        if not self.member_dropdown.value:
            self.labor_suggestion_container.visible = False
            self.selected_economic_activity_id = None
            if not self.editing_income_id:
                self.save_button.text = "💾 Guardar"
                self.form_title.value = "💰 Registrar ingreso"
                self.cancel_button.visible = False
            self.page.update()
            return

        try:
            member_id = int(self.member_dropdown.value)
        except ValueError:
            return

        activities = self.labor_controller.list_by_member(member_id)
        active_acts = [act for act in activities if act.is_active]

        # Verificar si el miembro ya tiene un sueldo recurrente registrado
        existing_incomes = self.income_controller.list_by_member(member_id)
        existing_recurring = next(
            (
                inc
                for inc in existing_incomes
                if inc.es_recurrente
                and inc.categoria
                in (
                    IncomeCategory.SUELDO,
                    IncomeCategory.FREELANCE,
                    IncomeCategory.JUBILADO,
                )
            ),
            None,
        )

        if not active_acts:
            self.labor_suggestion_container.visible = False
            self.selected_economic_activity_id = None
            if existing_recurring and not self.editing_income_id:
                self.editing_income_id = existing_recurring.id
                self.monto_input.value = str(existing_recurring.monto)
                self.descripcion_input.value = existing_recurring.descripcion
                self.categoria_dropdown.value = existing_recurring.categoria.name
                self.concept_dropdown.value = existing_recurring.concept or "salary"
                self.recurrente_checkbox.value = True
                self.frecuencia_dropdown.value = (
                    existing_recurring.frecuencia.name
                    if existing_recurring.frecuencia
                    else "MENSUAL"
                )
                self.frecuencia_dropdown.visible = True
                self.save_button.text = "🔄 Actualizar Sueldo Existente"
                self.form_title.value = "✏️ Actualizar ingreso recurrente"
                self.cancel_button.visible = True
            self.page.update()
            return

        act = active_acts[0]
        self.selected_economic_activity_id = act.id

        is_update = existing_recurring is not None
        btn_action_label = "Actualizar" if is_update else "Cargar"
        existing_id = existing_recurring.id if existing_recurring else None

        if act.nature == ActivityNature.DEPENDIENTE and act.dependent_details:
            details = act.dependent_details
            nom = details.estimated_monthly_nominal or Decimal("0.00")
            withholdings = LaborCalculationEngine.calculate_withholdings(
                nominal=nom,
                profile=details.tax_profile,
            )
            liquid = withholdings.liquid_amount
            nom_fmt = format_currency(nom, "UYU")
            liq_fmt = format_currency(liquid, "UYU")

            self.labor_suggestion_container.content = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.AUTO_AWESOME,
                            color=ft.Colors.TEAL_800,
                            size=20,
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(
                                    f"💼 Actividad: {act.title}",
                                    size=13,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.TEAL_900,
                                ),
                                ft.Text(
                                    f"Nominal: {nom_fmt} | Líquido en mano: {liq_fmt}",
                                    size=12,
                                    color=ft.Colors.TEAL_800,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        CorrectElevatedButton(
                            f"⚡ {btn_action_label} {liq_fmt} (Líquido)",
                            on_click=lambda _: self._fill_labor_income(
                                act=act,
                                amount=liquid,
                                description="Cobro de sueldo mensual",
                                category=IncomeCategory.SUELDO,
                                concept="salary",
                                existing_income_id=existing_id,
                            ),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=ft.Colors.LIGHT_BLUE_50,
                border=ft.Border.all(1.5, ft.Colors.LIGHT_BLUE_200),
                border_radius=8,
                padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                shadow=ft.BoxShadow(
                    spread_radius=1,
                    blur_radius=6,
                    color=ft.Colors.BLUE_GREY_100,
                    offset=ft.Offset(0, 2),
                ),
            )
            self.labor_suggestion_container.visible = True

        elif act.nature == ActivityNature.INDEPENDIENTE and act.independent_profile:
            ip = act.independent_profile
            sales = ip.estimated_monthly_gross_sales or Decimal("0.00")
            sales_fmt = format_currency(sales, "UYU")

            self.labor_suggestion_container.content = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.BUILD_OUTLINED,
                            color=ft.Colors.TEAL_800,
                            size=20,
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(
                                    f"🛠️ Actividad: {act.title}",
                                    size=13,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.TEAL_900,
                                ),
                                ft.Text(
                                    f"Facturación estimada: {sales_fmt}",
                                    size=12,
                                    color=ft.Colors.TEAL_800,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        CorrectElevatedButton(
                            f"⚡ {btn_action_label} {sales_fmt}",
                            on_click=lambda _: self._fill_labor_income(
                                act=act,
                                amount=sales,
                                description=f"Ingreso por {act.title}",
                                category=IncomeCategory.FREELANCE,
                                concept="salary",
                                existing_income_id=existing_id,
                            ),
                        )
                        if sales > 0
                        else ft.Container(),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=ft.Colors.LIGHT_BLUE_50,
                border=ft.Border.all(1.5, ft.Colors.LIGHT_BLUE_200),
                border_radius=8,
                padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                shadow=ft.BoxShadow(
                    spread_radius=1,
                    blur_radius=6,
                    color=ft.Colors.BLUE_GREY_100,
                    offset=ft.Offset(0, 2),
                ),
            )
            self.labor_suggestion_container.visible = True

        elif act.nature == ActivityNature.PASIVIDAD and act.pension_profile:
            pp = act.pension_profile
            pension_nom = pp.monthly_pension_nominal or Decimal("0.00")
            pension_fmt = format_currency(pension_nom, "UYU")

            self.labor_suggestion_container.content = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.SAVINGS_OUTLINED,
                            color=ft.Colors.TEAL_800,
                            size=20,
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(
                                    f"👴 Actividad: {act.title}",
                                    size=13,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.TEAL_900,
                                ),
                                ft.Text(
                                    f"Pasividad nominal: {pension_fmt}",
                                    size=12,
                                    color=ft.Colors.TEAL_800,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        CorrectElevatedButton(
                            f"⚡ {btn_action_label} {pension_fmt}",
                            on_click=lambda _: self._fill_labor_income(
                                act=act,
                                amount=pension_nom,
                                description="Cobro de pasividad / jubilación",
                                category=IncomeCategory.JUBILADO,
                                concept="salary",
                                existing_income_id=existing_id,
                            ),
                        )
                        if pension_nom > 0
                        else ft.Container(),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=ft.Colors.LIGHT_BLUE_50,
                border=ft.Border.all(1.5, ft.Colors.LIGHT_BLUE_200),
                border_radius=8,
                padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                shadow=ft.BoxShadow(
                    spread_radius=1,
                    blur_radius=6,
                    color=ft.Colors.BLUE_GREY_100,
                    offset=ft.Offset(0, 2),
                ),
            )
            self.labor_suggestion_container.visible = True
        else:
            self.labor_suggestion_container.visible = False

        self.page.update()

    def _fill_labor_income(
        self,
        act: EconomicActivity,
        amount: Decimal,
        description: str,
        category: IncomeCategory,
        concept: str,
        existing_income_id: int | None = None,
    ) -> None:
        """Autocompleta el formulario con datos de la actividad económica."""
        formatted_amount = (
            str(amount.quantize(Decimal("1")))
            if amount == amount.to_integral()
            else str(amount.quantize(Decimal("0.01")))
        )
        self.monto_input.value = formatted_amount
        self.descripcion_input.value = description
        self.categoria_dropdown.value = category.name
        self.concept_dropdown.value = concept
        self.selected_economic_activity_id = act.id
        self.currency_dropdown.value = "UYU"
        self.recurrente_checkbox.value = True
        self.frecuencia_dropdown.value = "MENSUAL"
        self.frecuencia_dropdown.visible = True

        if existing_income_id:
            self.editing_income_id = existing_income_id
            self.save_button.text = "🔄 Actualizar Sueldo Existente"
            self.form_title.value = "✏️ Actualizar ingreso recurrente"
            self.cancel_button.visible = True
        else:
            self.editing_income_id = None
            self.save_button.text = "💾 Guardar Sueldo Recurrente"
            self.form_title.value = "💰 Registrar ingreso"
            self.cancel_button.visible = False

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
            except (ValueError, InvalidOperation):
                self._show_error(
                    AppError(message="Fecha inválida. Use formato YYYY-MM-DD")
                )
                return

            # Parsear monto de forma segura con regla Decimal estricta
            parsed_monto = parse_decimal(self.monto_input.value)
            if parsed_monto.is_err():
                self._show_error(parsed_monto.unwrap_err())
                return
            monto = parsed_monto.unwrap()

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
                    frecuencia = RecurrenceFrequency[self.frecuencia_dropdown.value]
                except KeyError:
                    pass

            income = Income(
                id=self.editing_income_id,
                family_member_id=int(self.member_dropdown.value),
                economic_activity_id=self.selected_economic_activity_id,
                concept=self.concept_dropdown.value or "salary",
                monto=monto,
                currency=self.currency_dropdown.value or "UYU",
                fecha=fecha,
                descripcion=self.descripcion_input.value,
                categoria=categoria,
                es_recurrente=es_recurrente,
                frecuencia=frecuencia,
                notas=None,
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

                monto_formateado = format_currency_with_symbol(
                    income.monto, currency=income.currency
                )
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
                        padding=ft.Padding.symmetric(horizontal=6, vertical=2),
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
                                    size=30,
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
                                                f"{monto_formateado} • "
                                                f"{income.fecha}"
                                            ),
                                            size=12,
                                            color=ft.Colors.TEAL_700,
                                        ),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.EDIT,
                                    tooltip="Editar",
                                    icon_color=ft.Colors.TEAL_400,
                                    on_click=(
                                        lambda e, inc=income: self._on_edit_income(inc)
                                    ),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE,
                                    tooltip="Eliminar",
                                    icon_color=ft.Colors.RED_400,
                                    on_click=lambda e, inc=income: (
                                        self._on_delete_income(inc)
                                    ),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.START,
                        ),
                        padding=15,
                        bgcolor=ft.Colors.CYAN_50,
                        border=ft.Border.all(2, ft.Colors.TEAL_200),
                        border_radius=10,
                        shadow=ft.BoxShadow(
                            spread_radius=1,
                            blur_radius=4,
                            color=ft.Colors.TEAL_100,
                        ),
                    )
                )

        self.page.update()

    def _render_summary(self) -> None:
        """Renderizar resumen por categorías del mes, separado por moneda."""
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
            # Agrupar por moneda
            by_currency: dict[str, dict[str, Decimal]] = {}
            for (categoria, currency), monto in summary.items():
                by_currency.setdefault(currency, {})[categoria] = monto

            for currency, cat_summary in by_currency.items():
                total = sum(cat_summary.values(), Decimal("0"))
                total_formateado = format_currency_with_symbol(total, currency=currency)

                # Agregar total por moneda
                self.summary_column.controls.append(
                    ft.Text(
                        value=f"💰 Total de ingresos {currency}: {total_formateado}",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.GREEN,
                    )
                )

                self.summary_column.controls.append(ft.Divider())

                # Ordenar por monto descendente
                sorted_summary = sorted(
                    cat_summary.items(), key=lambda x: x[1], reverse=True
                )

                for categoria, monto in sorted_summary:
                    porcentaje = float(monto / total * 100) if total > 0 else 0.0
                    monto_formateado = format_currency_with_symbol(
                        monto, currency=currency
                    )

                    self.summary_column.controls.append(
                        ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Text(
                                            value=categoria,
                                            weight=ft.FontWeight.BOLD,
                                            expand=True,
                                        ),
                                        ft.Text(
                                            value=(
                                                f"{monto_formateado} "
                                                f"({porcentaje:.1f}%)"
                                            )
                                        ),
                                    ],
                                ),
                                ft.ProgressBar(
                                    value=porcentaje / 100,
                                    color=ft.Colors.GREEN,
                                    bgcolor=ft.Colors.GREEN_100,
                                ),
                            ],
                            spacing=5,
                        )
                    )

                self.summary_column.controls.append(ft.Divider())

        self.page.update()

    def _on_edit_income(self, income: Income) -> None:
        """Cargar datos del ingreso para editar"""
        self.editing_income_id = income.id
        self.selected_economic_activity_id = income.economic_activity_id
        self.member_dropdown.value = str(income.family_member_id)
        self.monto_input.value = str(income.monto)
        self.descripcion_input.value = income.descripcion
        self.categoria_dropdown.value = income.categoria.name
        self.concept_dropdown.value = income.concept or "salary"
        self.fecha_input.value = str(income.fecha)
        self.currency_dropdown.value = income.currency
        self.recurrente_checkbox.value = income.es_recurrente
        self.frecuencia_dropdown.visible = income.es_recurrente
        self.frecuencia_dropdown.value = (
            income.frecuencia.name if income.frecuencia else None
        )
        self.save_button.text = "✅ Actualizar"
        self.form_title.value = "✏️ Editar ingreso"
        self.cancel_button.visible = True
        self._on_member_selected(None)
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
        self.concept_dropdown.value = "salary"
        self.fecha_input.value = str(date.today())
        self.recurrente_checkbox.value = False
        self.frecuencia_dropdown.value = None
        self.frecuencia_dropdown.visible = False
        self.selected_economic_activity_id = None
        self.editing_income_id = None
        self.labor_suggestion_container.visible = False
        self.save_button.text = "💾 Guardar"
        self.form_title.value = "💰 Registrar ingreso"
        self.cancel_button.visible = False

        self.currency_dropdown.value = "UYU"

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
