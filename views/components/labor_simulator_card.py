"""
Componente reactivo para simulación interactiva de perfiles y regímenes
laborales uruguayos. Captura hechos en UI -> Invoca LaborController -> Presenta
CalculationResult. Cero lógica tributaria en UI. Decimal absoluto.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import flet as ft

from controllers.labor_controller import LaborController, parse_decimal
from services.labor.domain.dtos import IndependentProfile, PensionProfile
from services.labor.domain.enums import (
    ActivityNature,
    CalculationStatus,
    EligibilityStatus,
    FonasaBeneficiaryType,
    IndependentTaxRegime,
    PensionFundType,
)
from services.labor.domain.models import CalculationResult, TaxProfile
from utils.formatters import format_currency


class LaborSimulatorCard:
    """Tarjeta interactiva de simulación y desglose laboral/tributario."""

    def __init__(
        self,
        page: ft.Page,
        familia_id: int | None = None,
        on_activity_saved: Any | None = None,
    ) -> None:
        self.page = page
        self.controller = LaborController(familia_id=familia_id)
        self.on_activity_saved = on_activity_saved

        # Estado local de simulación (100% en memoria / Read-Only)
        self.selected_regime = ActivityNature.DEPENDIENTE
        self.current_result: CalculationResult | None = None
        self.current_error: str | None = None

        # --- Controles de Régimen y Tipo ---
        self.regime_dropdown = ft.Dropdown(
            label="Régimen / Actividad Económica",
            value=ActivityNature.DEPENDIENTE,
            options=[
                ft.dropdown.Option(
                    ActivityNature.DEPENDIENTE,
                    "💼 Dependiente (Mensual / Jornalero)",
                ),
                ft.dropdown.Option(
                    ActivityNature.INDEPENDIENTE,
                    "🛠️ Independiente / Servicios / Empresa",
                ),
                ft.dropdown.Option(
                    ActivityNature.PASIVIDAD,
                    "👴 Jubilado / Pensionista (IASS)",
                ),
            ],
            on_select=self._on_regime_change,
            expand=True,
        )

        # --- Sub-régimen para Independientes ---
        self.independent_subregime_dropdown = ft.Dropdown(
            label="Tipo de Régimen Independiente",
            value=IndependentTaxRegime.SERVICIOS_PERSONALES,
            options=[
                ft.dropdown.Option(
                    IndependentTaxRegime.SERVICIOS_PERSONALES,
                    "Servicios Personales (CJPPU / BPS)",
                ),
                ft.dropdown.Option(
                    IndependentTaxRegime.LITERAL_E,
                    "Pequeña Empresa (Literal E - IVA Exento)",
                ),
                ft.dropdown.Option(
                    IndependentTaxRegime.MONOTRIBUTO,
                    "Monotributo Común",
                ),
                ft.dropdown.Option(
                    IndependentTaxRegime.MONOTRIBUTO_MIDES,
                    "Monotributo Social MIDES",
                ),
            ],
            on_select=self._on_subregime_change,
            visible=False,
            expand=True,
        )

        # --- Inputs Dependiente ---
        self.nominal_input = ft.TextField(
            label="Sueldo Nominal Mensual ($)",
            hint_text="Ej: 75000.00",
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True,
            on_change=self._trigger_simulation,
        )
        self.children_input = ft.TextField(
            label="Hijos menores a cargo",
            value="0",
            hint_text="0",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=140,
            on_change=self._trigger_simulation,
        )
        self.spouse_switch = ft.Switch(
            label="Cónyuge/Concubino a cargo",
            value=False,
            on_change=self._trigger_simulation,
        )
        self.fonasa_dropdown = ft.Dropdown(
            label="Situación FONASA",
            value=FonasaBeneficiaryType.SINGLE_NO_CHILDREN,
            options=[
                ft.dropdown.Option(
                    FonasaBeneficiaryType.SINGLE_NO_CHILDREN,
                    "Sin hijos ni cónyuge a cargo",
                ),
                ft.dropdown.Option(
                    FonasaBeneficiaryType.WITH_CHILDREN_NO_SPOUSE,
                    "Con hijos a cargo (sin cónyuge)",
                ),
                ft.dropdown.Option(
                    FonasaBeneficiaryType.NO_CHILDREN_WITH_SPOUSE,
                    "Con cónyuge a cargo (sin hijos)",
                ),
                ft.dropdown.Option(
                    FonasaBeneficiaryType.WITH_CHILDREN_AND_SPOUSE,
                    "Con hijos y cónyuge a cargo",
                ),
            ],
            on_select=self._trigger_simulation,
            expand=True,
        )

        # --- Inputs Servicios Personales ---
        self.billed_input = ft.TextField(
            label="Facturación Neta Bimestral / Mensual ($)",
            hint_text="Ej: 90000.00",
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True,
            on_change=self._trigger_simulation,
        )
        self.pension_fund_dropdown = ft.Dropdown(
            label="Caja de Aportación Previsional",
            value=PensionFundType.CJPPU,
            options=[
                ft.dropdown.Option(
                    PensionFundType.CJPPU,
                    "CJPPU (Caja Profesional)",
                ),
                ft.dropdown.Option(
                    PensionFundType.BPS,
                    "BPS (No profesional)",
                ),
            ],
            on_select=self._trigger_simulation,
            expand=True,
        )
        self.cjppu_category_dropdown = ft.Dropdown(
            label="Categoría CJPPU",
            value="1",
            options=[
                ft.dropdown.Option(str(i), f"Categoría {i}") for i in range(1, 11)
            ],
            on_select=self._trigger_simulation,
            width=150,
        )
        self.client_cede_switch = ft.Switch(
            label="Cliente CEDE (Retención IVA)",
            value=False,
            on_change=self._trigger_simulation,
        )
        self.irpf_withheld_input = ft.TextField(
            label="Retenciones IRPF Sufridas ($)",
            value="0.00",
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True,
            on_change=self._trigger_simulation,
        )

        # --- Inputs Literal E & Monotributo ---
        self.annual_sales_input = ft.TextField(
            label="Facturación Bruta Anual Proyectada ($)",
            hint_text="Ej: 1200000.00",
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True,
            on_change=self._trigger_simulation,
        )
        self.months_active_input = ft.TextField(
            label="Meses de Antigüedad Activa",
            value="12",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=150,
            on_change=self._trigger_simulation,
        )
        self.sqm_local_input = ft.TextField(
            label="Metros² del Local Comercial",
            value="15",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=150,
            on_change=self._trigger_simulation,
        )
        self.employees_input = ft.TextField(
            label="Cantidad de Dependientes",
            value="0",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=150,
            on_change=self._trigger_simulation,
        )

        # --- Inputs Pasividad / Jubilado ---
        self.pension_nominal_input = ft.TextField(
            label="Pasividad / Jubilación Nominal ($)",
            hint_text="Ej: 45000.00",
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True,
            on_change=self._trigger_simulation,
        )
        self.pension_fund_pasivo_dropdown = ft.Dropdown(
            label="Caja de Pasividad",
            value=PensionFundType.BPS,
            options=[
                ft.dropdown.Option(PensionFundType.BPS, "BPS (Común)"),
                ft.dropdown.Option(PensionFundType.CJPPU, "CJPPU (Profesionales)"),
                ft.dropdown.Option(PensionFundType.CAJA_BANCARIA, "Caja Bancaria"),
                ft.dropdown.Option(PensionFundType.CAJA_NOTARIAL, "Caja Notarial"),
                ft.dropdown.Option(PensionFundType.MILITAR, "Militar / Policial"),
            ],
            on_select=self._trigger_simulation,
            expand=True,
        )
        self.pension_fonasa_switch = ft.Switch(
            label="Aporte Fonasa Pasivo",
            value=True,
            on_change=self._trigger_simulation,
        )

        # Contenedores dinámicos
        self.inputs_container = ft.Column(spacing=10)
        self.results_container = ft.Column(spacing=10)

        # Inicialización
        self._sync_inputs_visibility()

    def _on_regime_change(self, e: Any) -> None:
        self.selected_regime = self.regime_dropdown.value or ActivityNature.DEPENDIENTE
        self.independent_subregime_dropdown.visible = (
            self.selected_regime == ActivityNature.INDEPENDIENTE
        )
        self._sync_inputs_visibility()
        self._trigger_simulation(None)

    def _on_subregime_change(self, e: Any) -> None:
        self._sync_inputs_visibility()
        self._trigger_simulation(None)

    def _sync_inputs_visibility(self) -> None:
        self.inputs_container.controls.clear()

        if self.selected_regime == ActivityNature.DEPENDIENTE:
            self.inputs_container.controls.extend(
                [
                    ft.ResponsiveRow(
                        [
                            ft.Container(
                                content=self.nominal_input,
                                col={"xs": 12, "sm": 7},
                            ),
                            ft.Container(
                                content=self.children_input,
                                col={"xs": 6, "sm": 5},
                            ),
                        ]
                    ),
                    ft.ResponsiveRow(
                        [
                            ft.Container(
                                content=self.fonasa_dropdown,
                                col={"xs": 12, "sm": 7},
                            ),
                            ft.Container(
                                content=self.spouse_switch,
                                col={"xs": 12, "sm": 5},
                            ),
                        ]
                    ),
                ]
            )
        elif self.selected_regime == ActivityNature.INDEPENDIENTE:
            sub = self.independent_subregime_dropdown.value
            if sub == IndependentTaxRegime.SERVICIOS_PERSONALES:
                self.inputs_container.controls.extend(
                    [
                        ft.ResponsiveRow(
                            [
                                ft.Container(
                                    content=self.billed_input,
                                    col={"xs": 12, "sm": 7},
                                ),
                                ft.Container(
                                    content=self.pension_fund_dropdown,
                                    col={"xs": 12, "sm": 5},
                                ),
                            ]
                        ),
                        ft.ResponsiveRow(
                            [
                                ft.Container(
                                    content=self.cjppu_category_dropdown,
                                    col={"xs": 6, "sm": 4},
                                ),
                                ft.Container(
                                    content=self.irpf_withheld_input,
                                    col={"xs": 6, "sm": 4},
                                ),
                                ft.Container(
                                    content=self.client_cede_switch,
                                    col={"xs": 12, "sm": 4},
                                ),
                            ]
                        ),
                    ]
                )
            elif sub == IndependentTaxRegime.LITERAL_E:
                self.inputs_container.controls.extend(
                    [
                        ft.ResponsiveRow(
                            [
                                ft.Container(
                                    content=self.annual_sales_input,
                                    col={"xs": 12, "sm": 8},
                                ),
                                ft.Container(
                                    content=self.months_active_input,
                                    col={"xs": 12, "sm": 4},
                                ),
                            ]
                        ),
                    ]
                )
            else:  # Monotributo
                self.inputs_container.controls.extend(
                    [
                        ft.ResponsiveRow(
                            [
                                ft.Container(
                                    content=self.annual_sales_input,
                                    col={"xs": 12, "sm": 6},
                                ),
                                ft.Container(
                                    content=self.sqm_local_input,
                                    col={"xs": 6, "sm": 3},
                                ),
                                ft.Container(
                                    content=self.employees_input,
                                    col={"xs": 6, "sm": 3},
                                ),
                            ]
                        ),
                    ]
                )
        elif self.selected_regime == ActivityNature.PASIVIDAD:
            self.inputs_container.controls.extend(
                [
                    ft.ResponsiveRow(
                        [
                            ft.Container(
                                content=self.pension_nominal_input,
                                col={"xs": 12, "sm": 6},
                            ),
                            ft.Container(
                                content=self.pension_fund_pasivo_dropdown,
                                col={"xs": 12, "sm": 6},
                            ),
                        ]
                    ),
                    ft.Row([self.pension_fonasa_switch]),
                ]
            )

        try:
            self.inputs_container.update()
            self.independent_subregime_dropdown.update()
        except Exception:
            pass

    def _trigger_simulation(self, e: Any) -> None:
        """Ejecuta el cálculo interactivo puro sin persistir ningún dato."""
        self.current_error = None
        self.current_result = None

        if self.selected_regime == ActivityNature.DEPENDIENTE:
            children_res = parse_decimal(self.children_input.value, Decimal("0"))
            children = int(children_res.unwrap_or(Decimal("0")))
            fonasa_val = (
                self.fonasa_dropdown.value or FonasaBeneficiaryType.SINGLE_NO_CHILDREN
            )
            if children > 0 and self.spouse_switch.value:
                fonasa_val = FonasaBeneficiaryType.WITH_CHILDREN_AND_SPOUSE
            elif children > 0:
                fonasa_val = FonasaBeneficiaryType.WITH_CHILDREN_NO_SPOUSE
            elif self.spouse_switch.value:
                fonasa_val = FonasaBeneficiaryType.NO_CHILDREN_WITH_SPOUSE

            tax_profile = TaxProfile(
                children_count=children,
                has_spouse_charge=bool(self.spouse_switch.value),
                fonasa_type=fonasa_val,
            )
            sim_res = self.controller.simulate_dependent(
                nominal_str=self.nominal_input.value or "0.00",
                tax_profile=tax_profile,
            )
            if sim_res.is_ok():
                self.current_result = sim_res.unwrap()
            else:
                self.current_error = str(sim_res.unwrap_err())

        elif self.selected_regime == ActivityNature.INDEPENDIENTE:
            sub = self.independent_subregime_dropdown.value
            if sub == IndependentTaxRegime.SERVICIOS_PERSONALES:
                cat = int(self.cjppu_category_dropdown.value or 1)
                fund = self.pension_fund_dropdown.value or PensionFundType.CJPPU
                profile = IndependentProfile(
                    regime=IndependentTaxRegime.SERVICIOS_PERSONALES,
                    pension_fund=fund,
                    is_professional=(fund == PensionFundType.CJPPU),
                    cjppu_category=cat if fund == PensionFundType.CJPPU else None,
                )
                sim_res = self.controller.simulate_personal_services(
                    billed_str=self.billed_input.value or "0.00",
                    profile=profile,
                    is_client_cede=bool(self.client_cede_switch.value),
                    withholdings_suffered_str=(
                        self.irpf_withheld_input.value or "0.00"
                    ),
                )
                if sim_res.is_ok():
                    self.current_result = sim_res.unwrap()
                else:
                    self.current_error = str(sim_res.unwrap_err())

            elif sub == IndependentTaxRegime.LITERAL_E:
                profile = IndependentProfile(
                    regime=IndependentTaxRegime.LITERAL_E,
                    pension_fund=PensionFundType.BPS,
                )
                sim_res = self.controller.simulate_literal_e(
                    annual_sales_str=self.annual_sales_input.value or "0.00",
                    profile=profile,
                )
                if sim_res.is_ok():
                    self.current_result = sim_res.unwrap()
                else:
                    self.current_error = str(sim_res.unwrap_err())

            else:  # Monotributo
                is_mides = sub == IndependentTaxRegime.MONOTRIBUTO_MIDES
                sqm_res = parse_decimal(self.sqm_local_input.value, Decimal("15"))
                emp_res = parse_decimal(self.employees_input.value, Decimal("0"))
                profile = IndependentProfile(
                    regime=(
                        IndependentTaxRegime.MONOTRIBUTO_MIDES
                        if is_mides
                        else IndependentTaxRegime.MONOTRIBUTO
                    ),
                    pension_fund=PensionFundType.BPS,
                    has_mides_certificate=is_mides,
                    local_premises_sqm=sqm_res.unwrap_or(Decimal("15")),
                    employees_count=int(emp_res.unwrap_or(Decimal("0"))),
                )
                sim_res = self.controller.simulate_monotributo(
                    annual_sales_str=self.annual_sales_input.value or "0.00",
                    profile=profile,
                )
                if sim_res.is_ok():
                    self.current_result = sim_res.unwrap()
                else:
                    self.current_error = str(sim_res.unwrap_err())

        elif self.selected_regime == ActivityNature.PASIVIDAD:
            pension_fund = (
                self.pension_fund_pasivo_dropdown.value or PensionFundType.BPS
            )
            parsed_nominal = parse_decimal(
                self.pension_nominal_input.value or "0.00"
            ).unwrap_or(Decimal("0.00"))
            profile = PensionProfile(
                pension_fund=pension_fund,
                monthly_pension_nominal=parsed_nominal,
                has_fonasa_coverage=bool(self.pension_fonasa_switch.value),
            )
            sim_res = self.controller.simulate_pension(profile=profile)
            if sim_res.is_ok():
                self.current_result = sim_res.unwrap()
            else:
                self.current_error = str(sim_res.unwrap_err())

        self._render_results()

    def _render_results(self) -> None:
        self.results_container.controls.clear()

        if self.current_error:
            self.results_container.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.WARNING_AMBER_ROUNDED,
                                color=ft.Colors.RED_600,
                            ),
                            ft.Text(
                                f"Error de entrada: {self.current_error}",
                                color=ft.Colors.RED_700,
                            ),
                        ]
                    ),
                    padding=10,
                    bgcolor=ft.Colors.RED_50,
                    border_radius=8,
                )
            )
            try:
                self.results_container.update()
            except Exception:
                pass
            return

        if not self.current_result:
            return

        res = self.current_result

        # Badge de Estado
        status_bg = ft.Colors.GREEN_100
        status_color = ft.Colors.GREEN_800
        status_text = "🟢 Cálculo Verificado (Definitivo)"
        if res.status == CalculationStatus.PROVISIONAL:
            status_bg = ft.Colors.AMBER_100
            status_color = ft.Colors.AMBER_900
            status_text = "🟡 Proyección Estimada"
        elif res.status == CalculationStatus.REQUIRES_REVIEW:
            status_bg = ft.Colors.ORANGE_100
            status_color = ft.Colors.ORANGE_900
            status_text = "🟠 Requiere Revisión"
        elif res.status == CalculationStatus.INSUFFICIENT_DATA:
            status_bg = ft.Colors.RED_100
            status_color = ft.Colors.RED_800
            status_text = "🔴 Datos Incompletos"

        status_badge = ft.Container(
            content=ft.Text(
                status_text,
                size=12,
                weight=ft.FontWeight.BOLD,
                color=status_color,
            ),
            padding=ft.Padding(8, 4, 8, 4),
            bgcolor=status_bg,
            border_radius=6,
        )

        alerts = []
        if res.eligibility and res.eligibility.status == EligibilityStatus.INELIGIBLE:
            for v in res.eligibility.violations:
                alerts.append(
                    ft.Text(
                        f"⛔ Inelegible: {v}",
                        color=ft.Colors.RED_700,
                        size=12,
                        weight=ft.FontWeight.BOLD,
                    )
                )
        if res.review_reasons:
            for r in res.review_reasons:
                alerts.append(
                    ft.Text(
                        f"⚠️ Observación: {r}",
                        color=ft.Colors.ORANGE_800,
                        size=12,
                    )
                )
        if res.missing_fields:
            for mf in res.missing_fields:
                alerts.append(
                    ft.Text(
                        f"❓ Campo requerido: {mf}",
                        color=ft.Colors.RED_800,
                        size=12,
                    )
                )

        breakdown_rows = []

        if self.selected_regime == ActivityNature.DEPENDIENTE:
            fonasa_pct = res.fonasa_effective_rate * Decimal("100")
            irpf_pct = res.irpf_marginal_rate * Decimal("100")
            breakdown_rows = [
                self._make_row(
                    "Sueldo Nominal Declarado:",
                    format_currency(res.nominal_amount, "UYU"),
                    is_bold=True,
                ),
                ft.Divider(height=1, color=ft.Colors.BLUE_GREY_100),
                self._make_row(
                    "(-) Aporte Jubilatorio Montepío (15%):",
                    f"- {format_currency(res.montepio_amount, 'UYU')}",
                    color=ft.Colors.RED_700,
                ),
                self._make_row(
                    "(-) Fondo Reconversión Laboral (0.1%):",
                    f"- {format_currency(res.frl_amount, 'UYU')}",
                    color=ft.Colors.RED_700,
                ),
                self._make_row(
                    f"(-) Seguro de Salud FONASA ({fonasa_pct:.1f}%):",
                    f"- {format_currency(res.fonasa_amount, 'UYU')}",
                    color=ft.Colors.RED_700,
                ),
                self._make_row(
                    f"(-) Retención Anticipo IRPF ({irpf_pct:.0f}% marg.):",
                    f"- {format_currency(res.irpf_net_withholding, 'UYU')}",
                    color=ft.Colors.RED_700,
                ),
                self._make_hero_result(
                    "Líquido Estimado en Mano",
                    format_currency(res.liquid_amount, "UYU"),
                    "Dinero real que ingresa al bolsillo",
                    is_income=True,
                ),
            ]
        elif self.selected_regime == ActivityNature.INDEPENDIENTE:
            sub = self.independent_subregime_dropdown.value
            if (
                sub == IndependentTaxRegime.SERVICIOS_PERSONALES
                and res.personal_services_payload
            ):
                p = res.personal_services_payload
                breakdown_rows = [
                    self._make_row(
                        "Facturación Neta Declarada:",
                        format_currency(p.vat_gross_billed, "UYU"),
                        is_bold=True,
                    ),
                    ft.Divider(height=1, color=ft.Colors.BLUE_GREY_100),
                    self._make_row(
                        "IVA Débito Fiscal Neto a Pagar:",
                        format_currency(p.vat_net_payable, "UYU"),
                        color=ft.Colors.RED_700,
                    ),
                    self._make_row(
                        "Anticipo Bimestral IRPF (DGI):",
                        format_currency(p.irpf_net_advance_payable, "UYU"),
                        color=ft.Colors.RED_700,
                    ),
                    self._make_row(
                        "Aporte Mensual CJPPU / BPS:",
                        format_currency(
                            p.cjppu_monthly_amount or p.bps_independent_amount,
                            "UYU",
                        ),
                        color=ft.Colors.INDIGO_700,
                    ),
                ]
            elif sub == IndependentTaxRegime.LITERAL_E and res.literal_e_payload:
                p = res.literal_e_payload
                sales_fmt = format_currency(p.annual_gross_sales_uyu, "UYU")
                breakdown_rows = [
                    self._make_row(
                        "Ventas Brutas Anuales:",
                        f"{sales_fmt} ({p.annual_gross_sales_ui:.0f} UI)",
                        is_bold=True,
                    ),
                    ft.Divider(height=1, color=ft.Colors.BLUE_GREY_100),
                    self._make_row(
                        "Cuota Fija Mensual DGI (IVA Exento):",
                        format_currency(p.dgi_monthly_fee, "UYU"),
                    ),
                    self._make_row(
                        "Aporte Patronal BPS Estimado:",
                        format_currency(p.bps_patronal_monthly_fee, "UYU"),
                    ),
                    self._make_hero_result(
                        "Total Obligaciones Mensuales",
                        format_currency(p.total_monthly_obligations, "UYU"),
                        "Total cuota DGI + BPS mensual",
                        is_income=False,
                    ),
                ]
            elif res.monotributo_payload:
                p = res.monotributo_payload
                reg_name = (
                    "Social MIDES (Subvencionado)"
                    if p.is_mides_regime
                    else "Monotributo Común"
                )
                sales_fmt = format_currency(p.annual_gross_sales_uyu, "UYU")
                breakdown_rows = [
                    self._make_row("Régimen:", reg_name, is_bold=True),
                    self._make_row(
                        "Ventas Brutas Anuales:",
                        f"{sales_fmt} ({p.annual_gross_sales_ui:.0f} UI)",
                    ),
                    self._make_hero_result(
                        "Cuota Unificada Mensual BPS/DGI",
                        format_currency(p.final_monthly_monotributo_fee, "UYU"),
                        "Aporte unificado mensual",
                        is_income=False,
                    ),
                ]
        elif self.selected_regime == ActivityNature.PASIVIDAD and res.iass_payload:
            p = res.iass_payload
            iass_pct = p.iass_marginal_rate * Decimal("100")
            breakdown_rows = [
                self._make_row(
                    "Pasividad Nominal:",
                    format_currency(p.gross_pension_amount, "UYU"),
                    is_bold=True,
                ),
                ft.Divider(height=1, color=ft.Colors.BLUE_GREY_100),
                self._make_row(
                    "(-) Retención FONASA Pasivo:",
                    f"- {format_currency(p.fonasa_pension_withholding, 'UYU')}",
                    color=ft.Colors.RED_700,
                ),
                self._make_row(
                    f"(-) Retención IASS ({iass_pct:.0f}% marg.):",
                    f"- {format_currency(p.iass_net_withholding, 'UYU')}",
                    color=ft.Colors.RED_700,
                ),
                self._make_hero_result(
                    "Pasividad Líquida Mensual",
                    format_currency(p.net_pension_liquid, "UYU"),
                    "Monto neto mensual a cobrar",
                    is_income=True,
                ),
            ]

        utc_str = res.calculated_at_utc.strftime("%Y-%m-%d %H:%M:%S")
        audit_controls = [
            ft.Text(
                f"Regla Aplicada: {res.rule_version}",
                size=11,
                color=ft.Colors.BLUE_GREY_800,
            ),
            ft.Text(
                f"Fecha/Hora UTC: {utc_str}",
                size=11,
                color=ft.Colors.BLUE_GREY_800,
            ),
        ]
        for ref in res.legal_references:
            audit_controls.append(
                ft.Text(f"📖 {ref}", size=11, color=ft.Colors.INDIGO_900)
            )

        audit_container = ft.Container(
            content=ft.Column(audit_controls, spacing=3),
            padding=10,
            bgcolor=ft.Colors.BLUE_GREY_50,
            border_radius=6,
            border=ft.Border.all(1, ft.Colors.BLUE_GREY_100),
        )

        result_card = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [status_badge],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    *([ft.Column(alerts, spacing=4)] if alerts else []),
                    *breakdown_rows,
                    ft.Divider(height=1, color=ft.Colors.BLUE_GREY_100),
                    ft.ExpansionTile(
                        leading=ft.Icons.GAVEL_OUTLINED,
                        title=ft.Text(
                            "Trazabilidad y Fundamento Legal (Auditoría)",
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_GREY_800,
                        ),
                        controls=[audit_container],
                    ),
                ],
                spacing=10,
            ),
            padding=16,
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1.5, ft.Colors.BLUE_200),
            border_radius=10,
        )

        self.results_container.controls.append(result_card)
        try:
            self.results_container.update()
        except Exception:
            pass

    def _make_hero_result(
        self,
        title: str,
        amount_str: str,
        subtitle: str,
        is_income: bool = True,
    ) -> ft.Container:
        """Crea un bloque visual destacado (Hero Box) para el monto neto final."""
        bg_color = ft.Colors.GREEN_50 if is_income else ft.Colors.INDIGO_50
        border_color = ft.Colors.GREEN_300 if is_income else ft.Colors.INDIGO_300
        icon_bg = ft.Colors.GREEN_100 if is_income else ft.Colors.INDIGO_100
        icon_color = ft.Colors.GREEN_800 if is_income else ft.Colors.INDIGO_800
        title_color = ft.Colors.GREEN_950 if is_income else ft.Colors.INDIGO_950
        amount_color = ft.Colors.GREEN_900 if is_income else ft.Colors.INDIGO_900
        sub_color = ft.Colors.GREEN_800 if is_income else ft.Colors.INDIGO_700
        icon_name = (
            ft.Icons.ACCOUNT_BALANCE_WALLET if is_income else ft.Icons.RECEIPT_LONG
        )

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Icon(
                                    icon_name,
                                    color=icon_color,
                                    size=22,
                                ),
                                padding=8,
                                bgcolor=icon_bg,
                                border_radius=8,
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text(
                                        title,
                                        size=13,
                                        weight=ft.FontWeight.BOLD,
                                        color=title_color,
                                    ),
                                    ft.Text(
                                        subtitle,
                                        size=11,
                                        color=sub_color,
                                    ),
                                ],
                                spacing=1,
                            ),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        expand=True,
                    ),
                    ft.Text(
                        amount_str,
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=amount_color,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            bgcolor=bg_color,
            border=ft.Border.all(1.5, border_color),
            border_radius=10,
            margin=ft.Margin.only(top=6),
        )

    def _make_row(
        self,
        label: str,
        value: str,
        is_bold: bool = False,
        is_highlight: bool = False,
        color: str | None = None,
    ) -> ft.Row:
        text_size = 14 if is_bold else 13
        weight = ft.FontWeight.BOLD if is_bold else ft.FontWeight.NORMAL
        val_color = color or ft.Colors.BLUE_GREY_900

        return ft.Row(
            controls=[
                ft.Text(
                    label,
                    size=text_size,
                    weight=weight,
                    color=(
                        ft.Colors.BLUE_GREY_700
                        if not is_bold
                        else ft.Colors.BLUE_GREY_900
                    ),
                    expand=True,
                ),
                ft.Text(
                    value,
                    size=text_size,
                    weight=weight,
                    color=val_color,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

    def render(self) -> ft.Control:
        """Renderiza la tarjeta del simulador interactivo."""
        self._trigger_simulation(None)

        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Icon(
                                    ft.Icons.LIGHTBULB_OUTLINE,
                                    color=ft.Colors.AMBER_900,
                                    size=20,
                                ),
                                ft.Text(
                                    "Proyectá el dinero líquido en mano, "
                                    "aportes de seguridad social y retenciones "
                                    "antes de tomar decisiones laborales.",
                                    size=12,
                                    weight=ft.FontWeight.W_500,
                                    color=ft.Colors.AMBER_950,
                                    expand=True,
                                ),
                            ],
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        bgcolor=ft.Colors.AMBER_50,
                        padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                        border_radius=8,
                        border=ft.Border.all(1, ft.Colors.AMBER_200),
                    ),
                    self.regime_dropdown,
                    self.independent_subregime_dropdown,
                    self.inputs_container,
                    ft.Divider(height=1, color=ft.Colors.BLUE_GREY_100),
                    self.results_container,
                ],
                spacing=12,
            ),
            padding=14,
            bgcolor=ft.Colors.BLUE_50,
            border_radius=10,
        )
