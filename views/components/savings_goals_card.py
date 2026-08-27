"""
Componente para la gestión interactiva de Metas de Ahorro Familiar (Alcancías 🐷).
Diseño en paleta pastel suave, paneles colapsables y simulación de plazos.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

import flet as ft

from controllers.family_member_controller import FamilyMemberController
from controllers.savings_goal_controller import SavingsGoalController
from models.savings_goal_model import (
    ContributionSource,
    GoalCategory,
    SavingsGoal,
)
from utils.formatters import format_currency


class SavingsGoalsCard(ft.Container):
    """
    Panel colapsable de Metas de Ahorro del Hogar (Alcancías Familiares).
    """

    def __init__(
        self,
        savings_controller: SavingsGoalController,
        member_controller: FamilyMemberController,
        on_refresh: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self.savings_controller = savings_controller
        self.member_controller = member_controller
        self.on_refresh_callback = on_refresh

        # Paleta pastel tenue
        self.bgcolor = ft.Colors.TEAL_50
        self.border = ft.Border.all(1.5, ft.Colors.TEAL_200)
        self.border_radius = 12
        self.padding = 14
        self.shadow = ft.BoxShadow(
            spread_radius=1,
            blur_radius=6,
            color=ft.Colors.BLUE_GREY_100,
            offset=ft.Offset(0, 2),
        )

        self._goals_list_column = ft.Column(spacing=10)
        self._expansion_tile = ft.ExpansionTile(
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.SAVINGS, color=ft.Colors.TEAL_800, size=24),
                    ft.Column(
                        controls=[
                            ft.Text(
                                "Metas de Ahorro del Hogar",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.TEAL_900,
                            ),
                            ft.Text(
                                "Alcancías familiares y proyección de metas",
                                size=12,
                                color=ft.Colors.TEAL_700,
                            ),
                        ],
                        spacing=1,
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
            ),
            expanded=False,
            controls=[
                ft.Container(
                    content=self._goals_list_column,
                    padding=ft.Padding.only(top=10, bottom=6),
                )
            ],
            bgcolor=ft.Colors.TRANSPARENT,
            collapsed_bgcolor=ft.Colors.TRANSPARENT,
            text_color=ft.Colors.TEAL_900,
            collapsed_text_color=ft.Colors.TEAL_900,
        )

        self.content = ft.Column(
            controls=[
                self._expansion_tile,
            ],
            spacing=0,
        )
        self.refresh()

    def refresh(self) -> None:
        """Recarga la lista de metas activas."""
        self._goals_list_column.controls.clear()
        goals = self.savings_controller.obtener_metas(activas_solo=False)

        # Barra superior con resumen y botón crear
        btn_nueva_meta = ft.ElevatedButton(
            "Nueva Meta",
            icon=ft.Icons.ADD,
            bgcolor=ft.Colors.TEAL_700,
            color=ft.Colors.WHITE,
            on_click=self._abrir_modal_crear_meta,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        )

        if not goals:
            self._goals_list_column.controls.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                "Aún no hay metas de ahorro configuradas.",
                                size=13,
                                color=ft.Colors.TEAL_800,
                                italic=True,
                            ),
                            btn_nueva_meta,
                        ],
                        spacing=10,
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=16,
                    alignment=ft.Alignment(0, 0),
                )
            )
            return

        # Encabezado con botón de agregar
        header_row = ft.Row(
            controls=[
                ft.Text(
                    f"{len(goals)} metas registradas",
                    size=13,
                    weight=ft.FontWeight.W_600,
                    color=ft.Colors.TEAL_900,
                ),
                btn_nueva_meta,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        self._goals_list_column.controls.append(header_row)

        for g in goals:
            card = self._render_goal_item(g)
            self._goals_list_column.controls.append(card)

    def _render_goal_item(self, goal: SavingsGoal) -> ft.Control:
        """Renderiza una tarjeta individual de meta de ahorro."""
        pct = goal.progress_pct
        pct_color = (
            ft.Colors.GREEN_700
            if pct >= 100
            else (ft.Colors.TEAL_700 if pct >= 50 else ft.Colors.AMBER_800)
        )

        target_str = format_currency(goal.target_amount, currency=goal.currency)
        current_str = format_currency(goal.current_amount, currency=goal.currency)
        remaining_str = format_currency(goal.remaining_amount, currency=goal.currency)

        # Barra de progreso suave
        progress_bar = ft.ProgressBar(
            value=min(pct / 100.0, 1.0),
            color=pct_color,
            bgcolor=ft.Colors.TEAL_100,
            height=8,
            border_radius=4,
        )

        # Botones de acción
        btn_aportar = ft.OutlinedButton(
            "Aportar",
            icon=ft.Icons.SAVINGS,
            on_click=lambda _, g=goal: self._abrir_modal_aportar(g),
            style=ft.ButtonStyle(
                color=ft.Colors.TEAL_800,
                side=ft.BorderSide(1, ft.Colors.TEAL_400),
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
        )

        btn_simular = ft.IconButton(
            icon=ft.Icons.AUTO_GRAPH,
            tooltip="Simular plazo con ingresos y aguinaldo",
            icon_color=ft.Colors.PURPLE_700,
            on_click=lambda _, g=goal: self._abrir_modal_simular(g),
        )

        btn_eliminar = ft.IconButton(
            icon=ft.Icons.DELETE_OUTLINE,
            tooltip="Eliminar meta",
            icon_color=ft.Colors.RED_400,
            on_click=lambda _, g=goal: self._confirmar_eliminar(g),
        )

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Icon(
                                        self._icon_for_category(goal.category),
                                        color=ft.Colors.TEAL_800,
                                        size=20,
                                    ),
                                    ft.Text(
                                        goal.name,
                                        size=14,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.BLUE_GREY_900,
                                    ),
                                ],
                                spacing=8,
                            ),
                            ft.Container(
                                content=ft.Text(
                                    f"{pct:.1f}%",
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                    color=pct_color,
                                ),
                                bgcolor=ft.Colors.WHITE,
                                border_radius=6,
                                padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                                border=ft.Border.all(1, ft.Colors.TEAL_200),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    progress_bar,
                    ft.Row(
                        controls=[
                            ft.Text(
                                f"Ahorrado: {current_str} de {target_str}",
                                size=12,
                                color=ft.Colors.BLUE_GREY_700,
                            ),
                            ft.Text(
                                f"Faltan: {remaining_str}",
                                size=12,
                                weight=ft.FontWeight.W_600,
                                color=ft.Colors.TEAL_900,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Row(
                        controls=[
                            btn_aportar,
                            ft.Row(controls=[btn_simular, btn_eliminar], spacing=0),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ],
                spacing=8,
            ),
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.TEAL_100),
            border_radius=10,
            padding=12,
        )

    def _icon_for_category(self, cat: GoalCategory) -> str:
        icons_map = {
            GoalCategory.VEHICLE: ft.Icons.DIRECTIONS_CAR,
            GoalCategory.TRAVEL: ft.Icons.FLIGHT,
            GoalCategory.EMERGENCY: ft.Icons.HEALTH_AND_SAFETY,
            GoalCategory.HOME: ft.Icons.HOME,
            GoalCategory.EDUCATION: ft.Icons.SCHOOL,
            GoalCategory.GENERAL: ft.Icons.SAVINGS,
        }
        return icons_map.get(cat, ft.Icons.SAVINGS)

    # ── Modales de Interacción ──────────────────────────────────────────

    def _abrir_modal_crear_meta(self, _e: ft.ControlEvent) -> None:
        page = self.page
        if not page:
            return

        nombre_tf = ft.TextField(
            label="Nombre de la Meta",
            hint_text="ej: Vacaciones en Rocha, Cambio de Auto",
            border_radius=8,
            autofocus=True,
        )
        monto_tf = ft.TextField(
            label="Monto Objetivo",
            hint_text="ej: 50000",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=8,
        )
        moneda_dd = ft.Dropdown(
            label="Moneda",
            value="UYU",
            options=[
                ft.dropdown.Option("UYU", "Pesos Uruguayos ($)"),
                ft.dropdown.Option("USD", "Dólares Americanos (USD)"),
            ],
            border_radius=8,
        )
        categoria_dd = ft.Dropdown(
            label="Categoría",
            value=GoalCategory.GENERAL.value,
            options=[
                ft.dropdown.Option(GoalCategory.GENERAL.value, "General / Ahorro"),
                ft.dropdown.Option(GoalCategory.TRAVEL.value, "Viajes / Vacaciones"),
                ft.dropdown.Option(GoalCategory.VEHICLE.value, "Vehículo / Auto"),
                ft.dropdown.Option(GoalCategory.HOME.value, "Hogar / Reformas"),
                ft.dropdown.Option(GoalCategory.EMERGENCY.value, "Fondo de Emergencia"),
                ft.dropdown.Option(
                    GoalCategory.EDUCATION.value, "Educación / Estudios"
                ),
            ],
            border_radius=8,
        )

        error_txt = ft.Text(color=ft.Colors.RED_600, size=12, visible=False)

        def guardar(_):
            try:
                monto = Decimal(monto_tf.value or "0")
                if monto <= Decimal("0"):
                    error_txt.value = "El monto debe ser mayor a cero."
                    error_txt.visible = True
                    page.update()
                    return
                if not nombre_tf.value or not nombre_tf.value.strip():
                    error_txt.value = "El nombre es obligatorio."
                    error_txt.visible = True
                    page.update()
                    return

                res = self.savings_controller.crear_meta(
                    name=nombre_tf.value.strip(),
                    target_amount=monto,
                    currency=moneda_dd.value or "UYU",
                    category=GoalCategory(categoria_dd.value or "general"),
                )
                if res.is_ok():
                    dialog.open = False
                    self.refresh()
                    if self.on_refresh_callback:
                        self.on_refresh_callback()
                    page.update()
                else:
                    error_txt.value = str(res.err())
                    error_txt.visible = True
                    page.update()
            except Exception as ex:
                error_txt.value = f"Valor inválido: {ex}"
                error_txt.visible = True
                page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("🎯 Nueva Meta de Ahorro", weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        nombre_tf,
                        monto_tf,
                        moneda_dd,
                        categoria_dd,
                        error_txt,
                    ],
                    spacing=12,
                    tight=True,
                ),
                width=360,
            ),
            actions=[
                ft.TextButton(
                    "Cancelar",
                    on_click=lambda _: setattr(dialog, "open", False) or page.update(),
                ),
                ft.ElevatedButton(
                    "Crear Meta",
                    bgcolor=ft.Colors.TEAL_700,
                    color=ft.Colors.WHITE,
                    on_click=guardar,
                ),
            ],
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def _abrir_modal_aportar(self, goal: SavingsGoal) -> None:
        page = self.page
        if not page:
            return

        monto_tf = ft.TextField(
            label=f"Monto del Aporte ({goal.currency})",
            hint_text="ej: 5000",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=8,
            autofocus=True,
        )

        members_res = self.member_controller.get_all()
        members = members_res.ok() if members_res.is_ok() and members_res.ok() else []

        member_options = [ft.dropdown.Option("", "Aporte familiar conjunto")]
        for m in members:
            if m.id and m.activo:
                member_options.append(ft.dropdown.Option(str(m.id), m.nombre))

        member_dd = ft.Dropdown(
            label="¿Quién aporta?",
            value="",
            options=member_options,
            border_radius=8,
        )

        fuente_dd = ft.Dropdown(
            label="Fuente del Aporte",
            value=ContributionSource.REGULAR_INCOME.value,
            options=[
                ft.dropdown.Option(
                    ContributionSource.REGULAR_INCOME.value, "Ahorro mensual regular"
                ),
                ft.dropdown.Option(
                    ContributionSource.AGUINALDO_JUNE.value, "Aguinaldo de Junio"
                ),
                ft.dropdown.Option(
                    ContributionSource.AGUINALDO_DECEMBER.value,
                    "Aguinaldo de Diciembre",
                ),
                ft.dropdown.Option(
                    ContributionSource.VACATION_PAY.value, "Salario Vacacional"
                ),
                ft.dropdown.Option(
                    ContributionSource.EXTRA_INVOICE.value,
                    "Trabajo extra / Unipersonal",
                ),
                ft.dropdown.Option(
                    ContributionSource.MANUAL_DEPOSIT.value, "Depósito puntual"
                ),
            ],
            border_radius=8,
        )

        nota_tf = ft.TextField(
            label="Nota / Concepto (opcional)",
            hint_text="ej: Porción del aguinaldo",
            border_radius=8,
        )

        error_txt = ft.Text(color=ft.Colors.RED_600, size=12, visible=False)

        def registrar(_):
            try:
                monto = Decimal(monto_tf.value or "0")
                if monto <= Decimal("0"):
                    error_txt.value = "El monto debe ser mayor a cero."
                    error_txt.visible = True
                    page.update()
                    return

                mid = int(member_dd.value) if member_dd.value else None
                res = self.savings_controller.registrar_aporte(
                    goal_id=goal.id or 0,
                    amount=monto,
                    currency=goal.currency,
                    family_member_id=mid,
                    source_type=ContributionSource(fuente_dd.value or "regular_income"),
                    note=nota_tf.value.strip() if nota_tf.value else None,
                )
                if res.is_ok():
                    dialog.open = False
                    self.refresh()
                    if self.on_refresh_callback:
                        self.on_refresh_callback()
                    page.update()
                else:
                    error_txt.value = str(res.err())
                    error_txt.visible = True
                    page.update()
            except Exception as ex:
                error_txt.value = f"Valor inválido: {ex}"
                error_txt.visible = True
                page.update()

        dialog = ft.AlertDialog(
            title=ft.Text(f"🐷 Aportar a '{goal.name}'", weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        monto_tf,
                        member_dd,
                        fuente_dd,
                        nota_tf,
                        error_txt,
                    ],
                    spacing=12,
                    tight=True,
                ),
                width=360,
            ),
            actions=[
                ft.TextButton(
                    "Cancelar",
                    on_click=lambda _: setattr(dialog, "open", False) or page.update(),
                ),
                ft.ElevatedButton(
                    "Registrar Aporte",
                    bgcolor=ft.Colors.TEAL_700,
                    color=ft.Colors.WHITE,
                    on_click=registrar,
                ),
            ],
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def _abrir_modal_simular(self, goal: SavingsGoal) -> None:
        page = self.page
        if not page:
            return

        ahorro_mes_tf = ft.TextField(
            label=f"Ahorro Mensual del Hogar ({goal.currency})",
            value="5000" if goal.currency == "UYU" else "150",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=8,
        )

        aguinaldo_pct_tf = ft.TextField(
            label="% de Aguinaldos a Destinar",
            value="50",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=8,
        )

        resultado_container = ft.Column(spacing=8)

        def ejecutar_simulacion(_):
            try:
                ahorro_mes = Decimal(ahorro_mes_tf.value or "0")
                ag_pct = Decimal(aguinaldo_pct_tf.value or "50")
                sim = self.savings_controller.simular_meta_con_contexto_laboral(
                    goal_id=goal.id or 0,
                    monthly_savings=ahorro_mes,
                    aguinaldo_pct=ag_pct,
                )

                resultado_container.controls.clear()

                # Escenario regular
                if sim.months_regular_only is not None:
                    d_str = (
                        sim.estimated_date_regular_only.strftime("%B %Y")
                        if sim.estimated_date_regular_only
                        else "-"
                    )
                    resultado_container.controls.append(
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Text(
                                        "📅 Solo con Ahorro Mensual Regular:",
                                        size=12,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.BLUE_GREY_900,
                                    ),
                                    ft.Text(
                                        f"• Plazo: {sim.months_regular_only} meses "
                                        f"(Fecha: {d_str})",
                                        size=12,
                                        color=ft.Colors.BLUE_GREY_700,
                                    ),
                                ],
                                spacing=3,
                            ),
                            bgcolor=ft.Colors.BLUE_50,
                            padding=10,
                            border_radius=8,
                        )
                    )

                # Escenario con Aguinaldo / Boost Laboral
                if sim.months_with_labor_boost is not None:
                    d_boost_str = (
                        sim.estimated_date_with_labor_boost.strftime("%B %Y")
                        if sim.estimated_date_with_labor_boost
                        else "-"
                    )
                    resultado_container.controls.append(
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Text(
                                        "🚀 Con Inyección de Aguinaldos Legales:",
                                        size=12,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.PURPLE_900,
                                    ),
                                    ft.Text(
                                        f"• Plazo reducido a: "
                                        f"{sim.months_with_labor_boost} meses "
                                        f"(Fecha: {d_boost_str})",
                                        size=12,
                                        color=ft.Colors.PURPLE_800,
                                    ),
                                    ft.Text(
                                        sim.labor_boost_description,
                                        size=11,
                                        color=ft.Colors.PURPLE_600,
                                        italic=True,
                                    )
                                    if sim.labor_boost_description
                                    else ft.Container(),
                                ],
                                spacing=3,
                            ),
                            bgcolor=ft.Colors.PURPLE_50,
                            padding=10,
                            border_radius=8,
                        )
                    )

                page.update()
            except Exception as ex:
                resultado_container.controls.clear()
                resultado_container.controls.append(
                    ft.Text(f"Error: {ex}", color=ft.Colors.RED_600, size=12)
                )
                page.update()

        ejecutar_btn = ft.ElevatedButton(
            "Calcular Proyección",
            icon=ft.Icons.CALCULATE,
            bgcolor=ft.Colors.PURPLE_700,
            color=ft.Colors.WHITE,
            on_click=ejecutar_simulacion,
        )

        faltante_str = format_currency(goal.remaining_amount, currency=goal.currency)
        dialog = ft.AlertDialog(
            title=ft.Text(f"Proyección: '{goal.name}'", weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            f"Faltan {faltante_str} para la meta.",
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.TEAL_900,
                        ),
                        ahorro_mes_tf,
                        aguinaldo_pct_tf,
                        ejecutar_btn,
                        resultado_container,
                    ],
                    spacing=12,
                    tight=True,
                ),
                width=380,
            ),
            actions=[
                ft.TextButton(
                    "Cerrar",
                    on_click=lambda _: setattr(dialog, "open", False) or page.update(),
                ),
            ],
        )
        page.overlay.append(dialog)
        dialog.open = True
        ejecutar_simulacion(None)  # Simular con valores por defecto al abrir
        page.update()

    def _confirmar_eliminar(self, goal: SavingsGoal) -> None:
        page = self.page
        if not page:
            return

        def eliminar(_):
            if goal.id:
                self.savings_controller.eliminar_meta(goal.id)
                dialog.open = False
                self.refresh()
                if self.on_refresh_callback:
                    self.on_refresh_callback()
                page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("¿Eliminar meta?"),
            content=ft.Text(f"¿Estás seguro de eliminar la meta '{goal.name}'?"),
            actions=[
                ft.TextButton(
                    "Cancelar",
                    on_click=lambda _: setattr(dialog, "open", False) or page.update(),
                ),
                ft.ElevatedButton(
                    "Eliminar",
                    bgcolor=ft.Colors.RED_600,
                    color=ft.Colors.WHITE,
                    on_click=eliminar,
                ),
            ],
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()
