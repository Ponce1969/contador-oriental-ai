"""
Componente interactivo para la optimización de IRPF: Núcleo Familiar vs. Individual.
Cálculo de deducciones conjuntas y crédito fiscal del 8% por alquiler (Ley 18.083).
Diseño en paleta pastel suave con paneles colapsables. Cero lógica tributaria en UI.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import flet as ft

from controllers.labor_controller import LaborController, parse_decimal
from services.labor.domain.dtos import (
    FamilyIRPFOptimizerInput,
    FamilyIRPFOptimizerResult,
)
from utils.formatters import format_currency

if TYPE_CHECKING:
    from controllers.family_member_controller import FamilyMemberController


class FamilyIRPFOptimizerCard(ft.Container):
    """
    Panel interactivo de optimización tributaria DGI para matrimonios y concubinatos.
    """

    def __init__(
        self,
        labor_controller: LaborController,
        member_controller: FamilyMemberController | None = None,
    ) -> None:
        super().__init__()
        self.labor_controller = labor_controller
        self.member_controller = member_controller

        # Paleta pastel cálida
        self.bgcolor = ft.Colors.AMBER_50
        self.border = ft.Border.all(1.5, ft.Colors.AMBER_200)
        self.border_radius = 12
        self.padding = 14
        self.shadow = ft.BoxShadow(
            spread_radius=1,
            blur_radius=6,
            color=ft.Colors.BLUE_GREY_100,
            offset=ft.Offset(0, 2),
        )

        # Estado local
        self.current_result: FamilyIRPFOptimizerResult | None = None

        # Inputs Miembro 1
        self.m1_name_input = ft.TextField(
            label="Persona 1 (Titular)",
            value="Titular",
            text_size=13,
            dense=True,
            expand=True,
        )
        self.m1_salary_input = ft.TextField(
            label="Sueldo Nominal Mensual ($)",
            value="80000",
            text_size=13,
            dense=True,
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True,
        )

        # Inputs Miembro 2
        self.m2_name_input = ft.TextField(
            label="Persona 2 (Cónyuge / Pareja)",
            value="Cónyuge",
            text_size=13,
            dense=True,
            expand=True,
        )
        self.m2_salary_input = ft.TextField(
            label="Sueldo Nominal Mensual ($)",
            value="35000",
            text_size=13,
            dense=True,
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True,
        )

        # Deducciones y Créditos
        self.children_input = ft.TextField(
            label="Hijos a cargo (<18)",
            value="1",
            text_size=13,
            dense=True,
            width=130,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.disabled_children_input = ft.TextField(
            label="Hijos con discap.",
            value="0",
            text_size=13,
            dense=True,
            width=130,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        self.rent_input = ft.TextField(
            label="Alquiler Mensual ($)",
            value="22000",
            text_size=13,
            dense=True,
            expand=True,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.apply_rent_switch = ft.Switch(
            label="Crédito 8% Alquiler (Ley 18.083)",
            value=True,
            active_color=ft.Colors.AMBER_800,
        )

        self.results_container = ft.Column(spacing=12)

        self._build_ui()

    def _build_ui(self) -> None:
        """Construye la interfaz reactiva del optimizador."""
        header = ft.Row(
            controls=[
                ft.Icon(
                    ft.Icons.AUTO_AWESOME_OUTLINED,
                    color=ft.Colors.AMBER_900,
                    size=22,
                ),
                ft.Column(
                    controls=[
                        ft.Text(
                            "Optimizador IRPF: Núcleo Familiar vs. Individual",
                            size=15,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.AMBER_900,
                        ),
                        ft.Text(
                            "Simulador anual DGI con cómputo del 8% de "
                            "crédito por alquiler y deducciones por hijos",
                            size=11,
                            color=ft.Colors.AMBER_800,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
        )

        calc_btn = ft.ElevatedButton(
            "🧮 Simular y Comparar Opciones DGI",
            icon=ft.Icons.CALCULATE_OUTLINED,
            bgcolor=ft.Colors.AMBER_700,
            color=ft.Colors.WHITE,
            on_click=self._on_calculate_clicked,
        )

        body_content = ft.Column(
            controls=[
                ft.Text(
                    "1. Ingresos y Cónyuges del Hogar",
                    weight=ft.FontWeight.W_600,
                    size=12,
                    color=ft.Colors.BLUE_GREY_800,
                ),
                ft.Row(
                    controls=[self.m1_name_input, self.m1_salary_input],
                    spacing=10,
                ),
                ft.Row(
                    controls=[self.m2_name_input, self.m2_salary_input],
                    spacing=10,
                ),
                ft.Divider(height=1, color=ft.Colors.AMBER_200),
                ft.Text(
                    "2. Deducciones por Hijos y Crédito por Alquiler",
                    weight=ft.FontWeight.W_600,
                    size=12,
                    color=ft.Colors.BLUE_GREY_800,
                ),
                ft.Row(
                    controls=[
                        self.children_input,
                        self.disabled_children_input,
                    ],
                    spacing=10,
                ),
                ft.Row(
                    controls=[
                        self.rent_input,
                        self.apply_rent_switch,
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(
                    content=calc_btn,
                    alignment=ft.Alignment(0, 0),
                    padding=ft.Padding(0, 8, 0, 8),
                ),
                self.results_container,
            ],
            spacing=10,
        )

        self.content = ft.ExpansionTile(
            title=header,
            subtitle=ft.Text(
                "Compará si te conviene declarar como núcleo familiar y "
                "descontá el 8% de tus alquileres",
                size=11,
                color=ft.Colors.BLUE_GREY_700,
            ),
            expanded=False,
            controls=[
                ft.Container(
                    content=body_content,
                    padding=ft.Padding(4, 10, 4, 10),
                )
            ],
        )

    def _on_calculate_clicked(self, _e: ft.ControlEvent) -> None:
        """Ejecuta el cálculo determinístico en el controlador."""
        m1_nom_res = parse_decimal(self.m1_salary_input.value)
        m2_nom_res = parse_decimal(self.m2_salary_input.value)
        rent_res = parse_decimal(self.rent_input.value)

        m1_nom = m1_nom_res.unwrap() if m1_nom_res.is_ok() else Decimal("0.00")
        m2_nom = m2_nom_res.unwrap() if m2_nom_res.is_ok() else Decimal("0.00")
        rent_val = rent_res.unwrap() if rent_res.is_ok() else Decimal("0.00")

        try:
            children = int(self.children_input.value or "0")
        except ValueError:
            children = 0

        try:
            disabled = int(self.disabled_children_input.value or "0")
        except ValueError:
            disabled = 0

        # Anualizar
        m1_annual = m1_nom * Decimal("12")
        m2_annual = m2_nom * Decimal("12")
        rent_annual = rent_val * Decimal("12")

        # Cargas sociales promedio (~19.6%)
        ss_rate = Decimal("0.1960")
        m1_ss = (m1_annual * ss_rate).quantize(Decimal("0.01"))
        m2_ss = (m2_annual * ss_rate).quantize(Decimal("0.01"))

        # Estimación de retenciones mensuales pagadas a cuenta
        m1_withholdings = self._estimate_annual_withholdings(
            m1_nom, m1_ss / Decimal("12"), children
        )
        m2_withholdings = self._estimate_annual_withholdings(
            m2_nom, m2_ss / Decimal("12"), 0
        )

        inp = FamilyIRPFOptimizerInput(
            year=2026,
            member1_name=self.m1_name_input.value or "Persona 1",
            member1_annual_nominal=m1_annual,
            member1_annual_social_security=m1_ss,
            member1_monthly_withholdings_paid=m1_withholdings,
            member2_name=self.m2_name_input.value or "Persona 2",
            member2_annual_nominal=m2_annual,
            member2_annual_social_security=m2_ss,
            member2_monthly_withholdings_paid=m2_withholdings,
            children_count=children,
            disabled_children_count=disabled,
            annual_rent_paid=rent_annual,
            apply_rental_credit=self.apply_rent_switch.value or False,
        )

        opt_result = self.labor_controller.optimizar_irpf_familiar(inp)
        if opt_result.is_ok():
            self.current_result = opt_result.unwrap()
            self._render_results()
        else:
            self.results_container.controls = [
                ft.Text(
                    f"Error: {opt_result.unwrap_err().message}",
                    color=ft.Colors.RED_700,
                    size=12,
                )
            ]

        try:
            if self.page:
                self.page.update()
        except (RuntimeError, AttributeError):
            pass

    def _estimate_annual_withholdings(
        self, monthly_nominal: Decimal, monthly_ss: Decimal, children: int
    ) -> Decimal:
        """Estima las retenciones mensuales acumuladas durante el año."""
        res = self.labor_controller.simulate_dependent(
            nominal_str=str(monthly_nominal),
            fiscal_year=2026,
        )
        if res.is_ok():
            calc = res.unwrap()
            return (calc.irpf_net_withholding * Decimal("12")).quantize(Decimal("0.01"))
        return Decimal("0.00")

    def _render_results(self) -> None:
        """Renderiza los paneles comparativos y la recomendación oficial."""
        if not self.current_result:
            return

        r = self.current_result

        # Badge de recomendación
        is_nf = r.recommended_option == "NUCLEO_FAMILIAR"
        badge_bg = ft.Colors.GREEN_100 if is_nf else ft.Colors.BLUE_100
        badge_color = ft.Colors.GREEN_900 if is_nf else ft.Colors.BLUE_900
        badge_icon = ft.Icons.CHECK_CIRCLE_OUTLINE if is_nf else ft.Icons.INFO_OUTLINE

        verdict_card = ft.Container(
            bgcolor=badge_bg,
            border=ft.Border.all(
                1.5,
                ft.Colors.GREEN_300 if is_nf else ft.Colors.BLUE_300,
            ),
            border_radius=8,
            padding=12,
            content=ft.Row(
                controls=[
                    ft.Icon(badge_icon, color=badge_color, size=26),
                    ft.Column(
                        controls=[
                            ft.Text(
                                (
                                    "🎯 RECOMENDACIÓN DGI: "
                                    f"{'NÚCLEO FAMILIAR' if is_nf else 'INDIVIDUAL'}"
                                ),
                                weight=ft.FontWeight.BOLD,
                                size=13,
                                color=badge_color,
                            ),
                            ft.Text(
                                r.recommendation_summary,
                                size=12,
                                color=badge_color,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
            ),
        )

        m1_tax_str = format_currency(r.member1_summary.annual_net_tax, "UYU")
        m2_tax_str = format_currency(r.member2_summary.annual_net_tax, "UYU")
        indiv_tot_str = format_currency(r.total_individual_net_tax, "UYU")

        # Tarjeta 1: Liquidación Individual
        card_indiv = ft.Container(
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.BLUE_GREY_200),
            border_radius=8,
            padding=12,
            expand=True,
            content=ft.Column(
                controls=[
                    ft.Text(
                        "👤 Liquidación Individual Conjunta",
                        weight=ft.FontWeight.W_600,
                        size=13,
                        color=ft.Colors.BLUE_GREY_900,
                    ),
                    ft.Text(
                        f"• {r.member1_summary.member_name}: IRPF Neto {m1_tax_str}",
                        size=11,
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                    ft.Text(
                        f"• {r.member2_summary.member_name}: IRPF Neto {m2_tax_str}",
                        size=11,
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                    ft.Divider(height=1, color=ft.Colors.BLUE_GREY_100),
                    ft.Row(
                        controls=[
                            ft.Text(
                                "Total IRPF Anual:",
                                size=12,
                                weight=ft.FontWeight.W_600,
                            ),
                            ft.Text(
                                indiv_tot_str,
                                size=12,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.BLUE_GREY_900,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ],
                spacing=6,
            ),
        )

        fam_gross_str = format_currency(r.family_gross_income, "UYU")
        fam_ded_str = format_currency(r.family_deductions_amount, "UYU")
        fam_rent_str = format_currency(r.rental_credit_amount, "UYU")
        fam_net_str = format_currency(r.family_net_tax, "UYU")
        ded_pct = r.family_deduction_rate * 100

        # Tarjeta 2: Liquidación Núcleo Familiar
        card_family = ft.Container(
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(
                1.5,
                ft.Colors.AMBER_400 if is_nf else ft.Colors.BLUE_GREY_200,
            ),
            border_radius=8,
            padding=12,
            expand=True,
            content=ft.Column(
                controls=[
                    ft.Text(
                        "👨‍👩‍👧‍👦 Liquidación Núcleo Familiar",
                        weight=ft.FontWeight.W_600,
                        size=13,
                        color=ft.Colors.AMBER_900,
                    ),
                    ft.Text(
                        f"• Ingreso Conjunto: {fam_gross_str}",
                        size=11,
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                    ft.Text(
                        f"• Deducciones: -{fam_ded_str} ({ded_pct:.0f}%)",
                        size=11,
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                    ft.Text(
                        f"• Crédito Alquiler 8%: -{fam_rent_str}",
                        size=11,
                        color=ft.Colors.GREEN_700,
                        weight=ft.FontWeight.W_600
                        if r.rental_credit_amount > 0
                        else ft.FontWeight.NORMAL,
                    ),
                    ft.Divider(height=1, color=ft.Colors.AMBER_200),
                    ft.Row(
                        controls=[
                            ft.Text(
                                "IRPF Núcleo Final:",
                                size=12,
                                weight=ft.FontWeight.W_600,
                            ),
                            ft.Text(
                                fam_net_str,
                                size=12,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.AMBER_900,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ],
                spacing=6,
            ),
        )

        comparison_row = ft.Row(
            controls=[card_indiv, card_family],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        legal_notes_col = ft.Column(
            controls=[
                ft.Text(
                    f"ℹ️ {note}",
                    size=10.5,
                    color=ft.Colors.BLUE_GREY_600,
                    italic=True,
                )
                for note in r.legal_notes
            ],
            spacing=3,
        )

        self.results_container.controls = [
            verdict_card,
            comparison_row,
            legal_notes_col,
        ]
