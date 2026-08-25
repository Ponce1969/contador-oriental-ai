"""
Componente para la proyección interactiva de Aguindaldos (SAC - Ley 12.840)
y Salario Vacacional (Ley 16.101) para integrantes familiares dependientes.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import flet as ft

from controllers.family_member_controller import FamilyMemberController
from controllers.labor_controller import LaborController
from core.state import AppState
from services.labor.domain.enums import ActivityNature, CalculationStatus
from services.labor.domain.periods import AguinaldoPeriod
from utils.formatters import format_currency


class BenefitsProjectionCard(ft.Container):
    """
    Tarjeta interactiva que muestra la previsión del próximo Aguinaldo
    y Salario Vacacional para los integrantes del hogar.
    """

    def __init__(
        self,
        labor_controller: LaborController,
        member_controller: FamilyMemberController,
        reference_date: date | None = None,
        show_header: bool = True,
    ) -> None:
        super().__init__()
        self.labor_controller = labor_controller
        self.member_controller = member_controller
        self.reference_date = reference_date or date.today()
        self.show_header = show_header

        # Estilo de tarjeta pastel
        self.bgcolor = ft.Colors.PURPLE_50
        if show_header:
            self.border = ft.Border.all(1.5, ft.Colors.PURPLE_200)
            self.border_radius = 12
            self.padding = 16
            self.shadow = ft.BoxShadow(
                spread_radius=1,
                blur_radius=6,
                color=ft.Colors.BLUE_GREY_100,
                offset=ft.Offset(0, 2),
            )
        else:
            self.padding = 8

        self.content_column = ft.Column(spacing=12)
        self.content = self.content_column
        self.refresh()

    def refresh(self) -> None:
        """Recalcula y vuelve a renderizar las proyecciones."""
        self.content_column.controls.clear()
        is_mobile = AppState.device == "mobile"

        period = AguinaldoPeriod.for_date(self.reference_date)
        period_label = (
            f"Fracción Junio {period.year}"
            if period.semester == 1
            else f"Fracción Diciembre {period.year}"
        )
        accrual_range = (
            f"{period.start_date.strftime('%d/%m/%Y')} al "
            f"{period.end_date.strftime('%d/%m/%Y')}"
        )

        if self.show_header:
            # Encabezado completo
            self.content_column.controls.append(
                ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.CARD_GIFTCARD,
                            color=ft.Colors.PURPLE_800,
                            size=24,
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(
                                    "🎁 Previsión de Aguinaldo y Salario Vacacional",
                                    size=16 if is_mobile else 18,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.PURPLE_900,
                                ),
                                ft.Text(
                                    f"Próximo cobro: {period_label} (Devengo: {accrual_range})",
                                    size=12,
                                    color=ft.Colors.PURPLE_700,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
            self.content_column.controls.append(ft.Divider(color=ft.Colors.PURPLE_200))
        else:
            self.content_column.controls.append(
                ft.Text(
                    f"🗓️ Próximo cobro: {period_label} (Período: {accrual_range})",
                    size=12,
                    weight=ft.FontWeight.W_500,
                    color=ft.Colors.PURPLE_800,
                )
            )

        # Obtener miembros y actividades
        members = self.member_controller.list_active_members()
        activities = self.labor_controller.list_all_activities()

        dependent_acts = [
            act
            for act in activities
            if act.is_active
            and act.nature == ActivityNature.DEPENDIENTE
            and act.id is not None
        ]

        if not dependent_acts:
            self.content_column.controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.INFO_OUTLINE,
                                color=ft.Colors.PURPLE_700,
                                size=20,
                            ),
                            ft.Text(
                                "No hay integrantes con actividad dependiente activa. "
                                "Al guardar una actividad en Familia, aquí verás la proyección.",
                                size=13,
                                color=ft.Colors.PURPLE_900,
                                expand=True,
                            ),
                        ],
                        spacing=8,
                    ),
                    padding=10,
                    bgcolor=ft.Colors.PURPLE_100,
                    border_radius=8,
                )
            )
            return

        # Renderizar cada integrante con actividad
        for act in dependent_acts:
            member_name = "Integrante"
            for m in members:
                if m.id == act.family_member_id:
                    member_name = m.nombre
                    break

            # Calcular aguinaldo
            aguinaldo_res = self.labor_controller.calculate_aguinaldo(
                activity_id=act.id,  # type: ignore[arg-type]
                year=period.year,
                semester=period.semester,
                today=self.reference_date,
            )

            # Calcular salario vacacional (20 días base)
            vacation_res = self.labor_controller.calculate_vacation_pay(
                activity_id=act.id,  # type: ignore[arg-type]
                requested_days=20,
            )

            aguinaldo_amt_str = "$ 0"
            is_provisional = False
            if aguinaldo_res.is_ok():
                ag_result = aguinaldo_res.unwrap()
                aguinaldo_amt_str = format_currency(ag_result.final_amount, "UYU")
                is_provisional = ag_result.status == CalculationStatus.PROVISIONAL

            vacation_amt_str = "$ 0"
            if vacation_res.is_ok():
                vac_result = vacation_res.unwrap()
                vacation_amt_str = format_currency(vac_result.final_amount, "UYU")

            status_badge = ft.Container(
                content=ft.Text(
                    (
                        "Provisorio (meses a devengar)"
                        if is_provisional
                        else "Confirmado"
                    ),
                    size=10,
                    weight=ft.FontWeight.BOLD,
                    color=(
                        ft.Colors.AMBER_900 if is_provisional else ft.Colors.GREEN_900
                    ),
                ),
                bgcolor=(
                    ft.Colors.AMBER_100 if is_provisional else ft.Colors.GREEN_100
                ),
                border_radius=6,
                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
            )

            member_card = ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Text(
                                    f"👤 {member_name} — {act.title}",
                                    weight=ft.FontWeight.BOLD,
                                    size=14,
                                    color=ft.Colors.PURPLE_900,
                                    expand=True,
                                ),
                                status_badge,
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.ResponsiveRow(
                            controls=[
                                ft.Container(
                                    content=ft.Row(
                                        controls=[
                                            ft.Icon(
                                                ft.Icons.SAVINGS,
                                                color=ft.Colors.PURPLE_700,
                                                size=18,
                                            ),
                                            ft.Column(
                                                controls=[
                                                    ft.Text(
                                                        "Aguinaldo Estimado (SAC):",
                                                        size=11,
                                                        color=ft.Colors.PURPLE_800,
                                                    ),
                                                    ft.Text(
                                                        aguinaldo_amt_str,
                                                        size=15,
                                                        weight=ft.FontWeight.BOLD,
                                                        color=ft.Colors.PURPLE_900,
                                                    ),
                                                ],
                                                spacing=1,
                                            ),
                                        ],
                                        spacing=8,
                                    ),
                                    col={"xs": 12, "sm": 6},
                                ),
                                ft.Container(
                                    content=ft.Row(
                                        controls=[
                                            ft.Icon(
                                                ft.Icons.BEACH_ACCESS,
                                                color=ft.Colors.INDIGO_700,
                                                size=18,
                                            ),
                                            ft.Column(
                                                controls=[
                                                    ft.Text(
                                                        "Salario Vacacional (20 días):",
                                                        size=11,
                                                        color=ft.Colors.INDIGO_800,
                                                    ),
                                                    ft.Text(
                                                        vacation_amt_str,
                                                        size=15,
                                                        weight=ft.FontWeight.BOLD,
                                                        color=ft.Colors.INDIGO_900,
                                                    ),
                                                ],
                                                spacing=1,
                                            ),
                                        ],
                                        spacing=8,
                                    ),
                                    col={"xs": 12, "sm": 6},
                                ),
                            ],
                            spacing=8,
                            run_spacing=8,
                        ),
                    ],
                    spacing=6,
                ),
                padding=12,
                bgcolor=ft.Colors.INDIGO_50,
                border=ft.Border.all(1, ft.Colors.INDIGO_200),
                border_radius=8,
            )

            self.content_column.controls.append(member_card)
