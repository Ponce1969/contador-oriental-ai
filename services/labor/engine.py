"""
Motor de dominio y orquestador para cálculos laborales uruguayos.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from services.labor.calculations.aguinaldo import AguinaldoCalculator
from services.labor.calculations.family_irpf_optimizer import (
    calculate_family_irpf_optimization,
)
from services.labor.calculations.independent.literal_e import (
    calculate_literal_e_settlement,
)
from services.labor.calculations.independent.monotributo import (
    calculate_monotributo_settlement,
)
from services.labor.calculations.independent.personal_services_orchestrator import (
    calculate_personal_services_settlement,
)
from services.labor.calculations.irpf import (
    IRPFAnnualSettlementResult,
    calculate_annual_irpf_settlement,
)
from services.labor.calculations.pension.iass_calculator import (
    calculate_pension_settlement,
)
from services.labor.calculations.vacational import VacationPayCalculator
from services.labor.calculations.withholdings import (
    calculate_monthly_withholdings,
    estimate_nominal_from_liquid,
)
from services.labor.domain.dtos import (
    FamilyIRPFOptimizerInput,
    FamilyIRPFOptimizerResult,
    IndependentProfile,
    PensionProfile,
)
from services.labor.domain.enums import RemunerationType
from services.labor.domain.models import (
    CalculationRequest,
    CalculationResult,
    NominalEstimationResult,
    TaxProfile,
)
from services.labor.domain.tax_rules import (
    get_cjppu_ruleset,
    get_iass_ruleset,
    get_irpf_independent_ruleset,
    get_irpf_ruleset,
    get_iva_ruleset,
    get_literal_e_ruleset,
    get_monotributo_ruleset,
    get_social_security_ruleset,
    get_ui_value,
    get_verified_bpc,
)


class LaborCalculationEngine:
    """Orquestador de cálculos determinísticos del subdominio laboral uruguayo."""

    @staticmethod
    def calculate_aguinaldo(
        request: CalculationRequest, today: date | None = None
    ) -> CalculationResult:
        """Calcula el aguinaldo (fracción Junio o Diciembre) con trazabilidad."""
        return AguinaldoCalculator.calculate(request, today=today)

    @staticmethod
    def calculate_vacation_pay(
        request: CalculationRequest,
        remuneration_type: RemunerationType = RemunerationType.MENSUAL,
    ) -> CalculationResult:
        """Calcula el salario vacacional orientativo para días solicitados."""
        return VacationPayCalculator.calculate(
            request, remuneration_type=remuneration_type
        )

    @staticmethod
    def calculate_withholdings(
        nominal: Decimal,
        profile: TaxProfile,
        fiscal_year: int = 2026,
    ) -> CalculationResult:
        """Calcula las retenciones y cargas sociales para un salario nominal mensual."""
        bpc = get_verified_bpc(fiscal_year)
        ss_rules = get_social_security_ruleset(fiscal_year)
        irpf_rules = get_irpf_ruleset(fiscal_year)

        return calculate_monthly_withholdings(
            nominal=nominal,
            profile=profile,
            ss_rules=ss_rules,
            irpf_rules=irpf_rules,
            bpc=bpc,
        )

    @staticmethod
    def estimate_nominal(
        liquid: Decimal,
        profile: TaxProfile,
        fiscal_year: int = 2026,
        tolerance: Decimal = Decimal("0.01"),
    ) -> NominalEstimationResult:
        """Resuelve el salario nominal determinísticamente a partir del líquido."""
        bpc = get_verified_bpc(fiscal_year)
        ss_rules = get_social_security_ruleset(fiscal_year)
        irpf_rules = get_irpf_ruleset(fiscal_year)

        return estimate_nominal_from_liquid(
            liquid=liquid,
            profile=profile,
            ss_rules=ss_rules,
            irpf_rules=irpf_rules,
            bpc=bpc,
            tolerance=tolerance,
        )

    @staticmethod
    def calculate_annual_irpf(
        annual_nominal_gross: Decimal,
        annual_social_security_contributions: Decimal,
        total_monthly_withholdings_paid: Decimal,
        profile: TaxProfile,
        fiscal_year: int = 2026,
    ) -> IRPFAnnualSettlementResult | None:
        """Calcula la liquidación y ajuste anual de IRPF sobre remuneraciones reales."""
        bpc = get_verified_bpc(fiscal_year)
        irpf_rules = get_irpf_ruleset(fiscal_year)
        if bpc is None or irpf_rules is None:
            return None

        return calculate_annual_irpf_settlement(
            annual_nominal_gross=annual_nominal_gross,
            annual_social_security_contributions=annual_social_security_contributions,
            total_monthly_withholdings_paid=total_monthly_withholdings_paid,
            profile=profile,
            rules=irpf_rules,
            bpc=bpc,
        )

    @staticmethod
    def calculate_personal_services(
        net_billed_amount: Decimal,
        profile: IndependentProfile,
        fiscal_year: int = 2026,
        is_client_cede: bool = False,
        vat_rate_type: str = "BASIC",
        actual_documented_expenses: Decimal | None = None,
        irpf_withholdings_suffered: Decimal = Decimal("0.00"),
    ) -> CalculationResult:
        """Calcula la liquidación de Servicios Personales (IVA, IRPF, CJPPU)."""
        iva_rules = get_iva_ruleset(fiscal_year)
        irpf_rules = get_irpf_independent_ruleset(fiscal_year)
        cjppu_rules = get_cjppu_ruleset(fiscal_year)

        return calculate_personal_services_settlement(
            net_billed_amount=net_billed_amount,
            profile=profile,
            iva_rules=iva_rules,
            irpf_rules=irpf_rules,
            cjppu_rules=cjppu_rules,
            is_client_cede=is_client_cede,
            vat_rate_type=vat_rate_type,
            actual_documented_expenses=actual_documented_expenses,
            irpf_withholdings_suffered=irpf_withholdings_suffered,
        )

    @staticmethod
    def calculate_literal_e(
        annual_gross_sales_uyu: Decimal,
        profile: IndependentProfile,
        fiscal_year: int = 2026,
        calculation_date: date | None = None,
    ) -> CalculationResult:
        """Calcula la liquidación y elegibilidad de Pequeña Empresa (Literal E)."""
        rules = get_literal_e_ruleset(fiscal_year)
        ui_value = get_ui_value(fiscal_year)

        return calculate_literal_e_settlement(
            annual_gross_sales_uyu=annual_gross_sales_uyu,
            profile=profile,
            rules=rules,
            ui_value=ui_value,
            calculation_date=calculation_date,
        )

    @staticmethod
    def calculate_monotributo(
        annual_gross_sales_uyu: Decimal,
        profile: IndependentProfile,
        fiscal_year: int = 2026,
        calculation_date: date | None = None,
    ) -> CalculationResult:
        """Calcula la liquidación y elegibilidad de Monotributo Común / Social MIDES."""
        rules = get_monotributo_ruleset(fiscal_year)
        ui_value = get_ui_value(fiscal_year)

        return calculate_monotributo_settlement(
            annual_gross_sales_uyu=annual_gross_sales_uyu,
            profile=profile,
            rules=rules,
            ui_value=ui_value,
            calculation_date=calculation_date,
        )

    @staticmethod
    def calculate_pension(
        profile: PensionProfile,
        fiscal_year: int = 2026,
    ) -> CalculationResult:
        """Calcula la liquidación de pasividades e IASS (Ley 18.314 / Ley 20.124)."""
        rules = get_iass_ruleset(fiscal_year)
        bpc = get_verified_bpc(fiscal_year)

        return calculate_pension_settlement(
            profile=profile,
            rules=rules,
            bpc=bpc,
        )

    @staticmethod
    def optimize_family_irpf(
        inp: FamilyIRPFOptimizerInput,
    ) -> FamilyIRPFOptimizerResult | None:
        """
        Calcula y compara la liquidación anual de IRPF Individual vs. Núcleo Familiar.
        Incorpora deducciones por hijos y crédito por alquiler (8% Ley 18.083 / 18.719).
        """
        irpf_rules = get_irpf_ruleset(inp.year)
        bpc = get_verified_bpc(inp.year)
        if irpf_rules is None or bpc is None:
            return None

        return calculate_family_irpf_optimization(
            inp=inp,
            rules=irpf_rules,
            bpc=bpc,
        )
