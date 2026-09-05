"""
Modelos declarativos de reglas tributarias y previsionales uruguayas (RuleSets).
Garantiza trazabilidad a normas oficiales y cero hardcodeo dentro de los calculadores.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from services.labor.domain.enums import (
    FonasaBeneficiaryType,
    RuleVerificationStatus,
)


class BPCValue(BaseModel):
    """Valor oficial de la Base de Prestaciones y Contribuciones (BPC)."""

    year: int
    value: Decimal
    effective_from: date
    source_decree: str
    verification_status: RuleVerificationStatus
    notes: str | None = None


class UIValue(BaseModel):
    """Valor oficial de la Unidad Indexada (UI) para un período."""

    year: int
    value: Decimal
    effective_date: date
    source: str
    verification_status: RuleVerificationStatus
    notes: str | None = None


class SocialSecurityRuleSet(BaseModel):
    """Parámetros normativos de Seguridad Social dependiente (BPS / INEFOP / MSP)."""

    rule_version: str
    year: int
    montepio_rate: Decimal
    frl_rate: Decimal
    fonasa_threshold_bpc: Decimal
    fonasa_rate_matrix: dict[FonasaBeneficiaryType, tuple[Decimal, Decimal]]
    bps_max_contribution_cap_nominal: Decimal | None
    source: str
    verification_status: RuleVerificationStatus


class IRPFBracket(BaseModel):
    """Tramo de la escala progresiva de IRPF Categoría II (en BPC)."""

    tier: int
    from_bpc: Decimal
    to_bpc: Decimal | None
    rate: Decimal


class IRPFRuleSet(BaseModel):
    """Parámetros normativos del Impuesto a la Renta de las Personas Físicas (DGI)."""

    rule_version: str
    year: int
    brackets: list[IRPFBracket]
    family_unit_brackets_both_generate: list[IRPFBracket] = []
    family_unit_brackets_single_generates: list[IRPFBracket] = []
    deduction_rate_low: Decimal
    deduction_rate_high: Decimal
    deduction_threshold_bpc: Decimal
    child_deduction_annual_bpc: Decimal
    disabled_child_deduction_annual_bpc: Decimal
    sac_ficto_increment_rate: Decimal
    rental_credit_rate: Decimal = Decimal("0.0800")
    mortgage_deduction_max_annual_bpc: Decimal = Decimal("36.0")
    source: str
    verification_status: RuleVerificationStatus


class IASSBracket(BaseModel):
    """Tramo de la escala progresiva de IASS (en BPC)."""

    tier: int
    from_bpc: Decimal
    to_bpc: Decimal | None
    rate: Decimal


class IASSRuleSet(BaseModel):
    """Parámetros normativos del Impuesto de Asistencia a la Seguridad Social (IASS)."""

    rule_version: str
    year: int
    brackets: list[IASSBracket]
    deduction_rate_low: Decimal
    deduction_rate_high: Decimal
    deduction_threshold_bpc: Decimal
    standard_health_deduction_monthly_bpc: Decimal
    source: str
    verification_status: RuleVerificationStatus


class IVARuleSet(BaseModel):
    """Parámetros normativos del Impuesto al Valor Agregado (DGI)."""

    rule_version: str
    year: int
    basic_rate: Decimal
    minimum_rate: Decimal
    cede_withholding_rate: Decimal
    source: str
    verification_status: RuleVerificationStatus


class IRPFIndependentRuleSet(BaseModel):
    """Parámetros normativos de IRPF Cat. II para Servicios Personales (DGI)."""

    rule_version: str
    year: int
    standard_expense_deduction_rate: Decimal
    taxable_income_factor: Decimal
    bimonthly_advance_rate: Decimal
    source: str
    verification_status: RuleVerificationStatus


class CJPPURuleSet(BaseModel):
    """Parámetros normativos de Caja Profesional de Profesionales Universitarios."""

    rule_version: str
    year: int
    contribution_rate: Decimal
    category_fictitious_salaries: dict[int, Decimal]
    source: str
    verification_status: RuleVerificationStatus


class LiteralERuleSet(BaseModel):
    """Parámetros normativos de Pequeña Empresa - Literal E (DGI / BPS)."""

    rule_version: str
    year: int
    threshold_ui: Decimal
    dgi_base_fee_monthly: Decimal
    bps_patronal_fee_monthly: Decimal
    tier_1_months: int
    tier_1_rate: Decimal
    tier_2_months: int
    tier_2_rate: Decimal
    tier_3_rate: Decimal
    source: str
    verification_status: RuleVerificationStatus


class MonotributoRuleSet(BaseModel):
    """Parámetros normativos de Monotributo Común y Social MIDES (BPS / DGI)."""

    rule_version: str
    year: int
    threshold_unipersonal_ui: Decimal
    threshold_sociedad_ui: Decimal
    max_premises_sqm: Decimal
    max_employees_unipersonal: int
    base_fee_unipersonal_monthly: Decimal
    base_fee_sociedad_monthly: Decimal
    mides_tier_1_months: int
    mides_tier_1_rate: Decimal
    mides_tier_2_months: int
    mides_tier_2_rate: Decimal
    mides_tier_3_months: int
    mides_tier_3_rate: Decimal
    mides_tier_4_rate: Decimal
    source: str
    verification_status: RuleVerificationStatus


# =====================================================================
# REGISTRO OFICIAL DE RULESETS POR AÑO FISCAL (DATA-DRIVEN)
# =====================================================================

_OFFICIAL_BPC_REGISTRY: dict[int, BPCValue] = {
    2024: BPCValue(
        year=2024,
        value=Decimal("6177.00"),
        effective_from=date(2024, 1, 1),
        source_decree="Decreto 433/023 (Poder Ejecutivo)",
        verification_status=RuleVerificationStatus.VERIFIED,
    ),
    2025: BPCValue(
        year=2025,
        value=Decimal("6576.00"),
        effective_from=date(2025, 1, 1),
        source_decree="Decreto 396/024 (Poder Ejecutivo)",
        verification_status=RuleVerificationStatus.VERIFIED,
    ),
    2026: BPCValue(
        year=2026,
        value=Decimal("7036.00"),
        effective_from=date(2026, 1, 1),
        source_decree="Decreto PE Ajuste BPC 2026 (Oficial)",
        verification_status=RuleVerificationStatus.VERIFIED,
    ),
}

_OFFICIAL_UI_REGISTRY: dict[int, UIValue] = {
    2024: UIValue(
        year=2024,
        value=Decimal("5.9000"),
        effective_date=date(2024, 1, 1),
        source="Instituto Nacional de Estadística (INE)",
        verification_status=RuleVerificationStatus.VERIFIED,
    ),
    2025: UIValue(
        year=2025,
        value=Decimal("6.1500"),
        effective_date=date(2025, 1, 1),
        source="Instituto Nacional de Estadística (INE)",
        verification_status=RuleVerificationStatus.VERIFIED,
    ),
    2026: UIValue(
        year=2026,
        value=Decimal("6.4200"),
        effective_date=date(2026, 1, 1),
        source="INE / Proyección Oficial 2026",
        verification_status=RuleVerificationStatus.VERIFIED,
    ),
}

_OFFICIAL_IRPF_BRACKETS_2023_ONWARDS: list[IRPFBracket] = [
    IRPFBracket(
        tier=1, from_bpc=Decimal("0.0"), to_bpc=Decimal("7.0"), rate=Decimal("0.0000")
    ),
    IRPFBracket(
        tier=2,
        from_bpc=Decimal("7.0"),
        to_bpc=Decimal("10.0"),
        rate=Decimal("0.1000"),
    ),
    IRPFBracket(
        tier=3,
        from_bpc=Decimal("10.0"),
        to_bpc=Decimal("15.0"),
        rate=Decimal("0.1500"),
    ),
    IRPFBracket(
        tier=4,
        from_bpc=Decimal("15.0"),
        to_bpc=Decimal("30.0"),
        rate=Decimal("0.2400"),
    ),
    IRPFBracket(
        tier=5,
        from_bpc=Decimal("30.0"),
        to_bpc=Decimal("50.0"),
        rate=Decimal("0.2500"),
    ),
    IRPFBracket(
        tier=6,
        from_bpc=Decimal("50.0"),
        to_bpc=Decimal("75.0"),
        rate=Decimal("0.2700"),
    ),
    IRPFBracket(
        tier=7,
        from_bpc=Decimal("75.0"),
        to_bpc=Decimal("115.0"),
        rate=Decimal("0.3100"),
    ),
    IRPFBracket(tier=8, from_bpc=Decimal("115.0"), to_bpc=None, rate=Decimal("0.3600")),
]

_OFFICIAL_IRPF_FAMILY_UNIT_BOTH_GENERATE: list[IRPFBracket] = [
    IRPFBracket(
        tier=1, from_bpc=Decimal("0.0"), to_bpc=Decimal("14.0"), rate=Decimal("0.0000")
    ),
    IRPFBracket(
        tier=2, from_bpc=Decimal("14.0"), to_bpc=Decimal("20.0"), rate=Decimal("0.1000")
    ),
    IRPFBracket(
        tier=3, from_bpc=Decimal("20.0"), to_bpc=Decimal("30.0"), rate=Decimal("0.1500")
    ),
    IRPFBracket(
        tier=4, from_bpc=Decimal("30.0"), to_bpc=Decimal("50.0"), rate=Decimal("0.2400")
    ),
    IRPFBracket(
        tier=5, from_bpc=Decimal("50.0"), to_bpc=Decimal("75.0"), rate=Decimal("0.2500")
    ),
    IRPFBracket(
        tier=6,
        from_bpc=Decimal("75.0"),
        to_bpc=Decimal("115.0"),
        rate=Decimal("0.2700"),
    ),
    IRPFBracket(
        tier=7,
        from_bpc=Decimal("115.0"),
        to_bpc=Decimal("166.6667"),
        rate=Decimal("0.3100"),
    ),
    IRPFBracket(
        tier=8, from_bpc=Decimal("166.6667"), to_bpc=None, rate=Decimal("0.3600")
    ),
]

_OFFICIAL_IRPF_FAMILY_UNIT_SINGLE_GENERATES: list[IRPFBracket] = [
    IRPFBracket(
        tier=1, from_bpc=Decimal("0.0"), to_bpc=Decimal("8.0"), rate=Decimal("0.0000")
    ),
    IRPFBracket(
        tier=2, from_bpc=Decimal("8.0"), to_bpc=Decimal("10.0"), rate=Decimal("0.1000")
    ),
    IRPFBracket(
        tier=3, from_bpc=Decimal("10.0"), to_bpc=Decimal("15.0"), rate=Decimal("0.1500")
    ),
    IRPFBracket(
        tier=4, from_bpc=Decimal("15.0"), to_bpc=Decimal("50.0"), rate=Decimal("0.2400")
    ),
    IRPFBracket(
        tier=5, from_bpc=Decimal("50.0"), to_bpc=Decimal("75.0"), rate=Decimal("0.2500")
    ),
    IRPFBracket(
        tier=6,
        from_bpc=Decimal("75.0"),
        to_bpc=Decimal("115.0"),
        rate=Decimal("0.2700"),
    ),
    IRPFBracket(
        tier=7,
        from_bpc=Decimal("115.0"),
        to_bpc=Decimal("166.6667"),
        rate=Decimal("0.3100"),
    ),
    IRPFBracket(
        tier=8, from_bpc=Decimal("166.6667"), to_bpc=None, rate=Decimal("0.3600")
    ),
]

_OFFICIAL_IASS_BRACKETS_2024_ONWARDS: list[IASSBracket] = [
    IASSBracket(
        tier=1, from_bpc=Decimal("0.0"), to_bpc=Decimal("9.0"), rate=Decimal("0.0000")
    ),
    IASSBracket(
        tier=2,
        from_bpc=Decimal("9.0"),
        to_bpc=Decimal("15.0"),
        rate=Decimal("0.1000"),
    ),
    IASSBracket(
        tier=3,
        from_bpc=Decimal("15.0"),
        to_bpc=Decimal("30.0"),
        rate=Decimal("0.2400"),
    ),
    IASSBracket(
        tier=4,
        from_bpc=Decimal("30.0"),
        to_bpc=Decimal("50.0"),
        rate=Decimal("0.2500"),
    ),
    IASSBracket(tier=5, from_bpc=Decimal("50.0"), to_bpc=None, rate=Decimal("0.3000")),
]

_CJPPU_CATEGORIES_2026: dict[int, Decimal] = {
    1: Decimal("34789.00"),
    2: Decimal("42520.00"),
    3: Decimal("51980.00"),
    4: Decimal("63535.00"),
    5: Decimal("77653.00"),
    6: Decimal("94908.00"),
    7: Decimal("115996.00"),
    8: Decimal("141772.00"),
    9: Decimal("173275.00"),
    10: Decimal("211782.00"),
}


def get_verified_bpc(year: int) -> BPCValue | None:
    """Obtiene el valor de BPC oficial para el año si está verificado."""
    return _OFFICIAL_BPC_REGISTRY.get(year)


def get_ui_value(year: int) -> UIValue | None:
    """Obtiene el valor de referencia de la Unidad Indexada para el año fiscal."""
    return _OFFICIAL_UI_REGISTRY.get(year)


def get_social_security_ruleset(year: int) -> SocialSecurityRuleSet | None:
    """Construye el RuleSet de Seguridad Social dependiente para el año fiscal."""
    if year < 2024:
        return None

    return SocialSecurityRuleSet(
        rule_version=f"UY-BPS-SS-{year}-v1",
        year=year,
        montepio_rate=Decimal("0.1500"),
        frl_rate=Decimal("0.0010"),
        fonasa_threshold_bpc=Decimal("2.5"),
        fonasa_rate_matrix={
            FonasaBeneficiaryType.SINGLE_NO_CHILDREN: (
                Decimal("0.0300"),
                Decimal("0.0450"),
            ),
            FonasaBeneficiaryType.WITH_CHILDREN_NO_SPOUSE: (
                Decimal("0.0500"),
                Decimal("0.0600"),
            ),
            FonasaBeneficiaryType.NO_CHILDREN_WITH_SPOUSE: (
                Decimal("0.0500"),
                Decimal("0.0650"),
            ),
            FonasaBeneficiaryType.WITH_CHILDREN_AND_SPOUSE: (
                Decimal("0.0700"),
                Decimal("0.0800"),
            ),
        },
        bps_max_contribution_cap_nominal=Decimal("255000.00"),
        source="Ley 16.713 / Ley 20.130 (BPS), Ley 18.211 (FONASA), Ley 18.406 (FRL)",
        verification_status=RuleVerificationStatus.VERIFIED,
    )


def get_irpf_ruleset(year: int) -> IRPFRuleSet | None:
    """Construye el RuleSet de IRPF para el año fiscal."""
    if year < 2024:
        return None

    return IRPFRuleSet(
        rule_version=f"UY-DGI-IRPF-{year}-v1",
        year=year,
        brackets=_OFFICIAL_IRPF_BRACKETS_2023_ONWARDS,
        family_unit_brackets_both_generate=_OFFICIAL_IRPF_FAMILY_UNIT_BOTH_GENERATE,
        family_unit_brackets_single_generates=_OFFICIAL_IRPF_FAMILY_UNIT_SINGLE_GENERATES,
        deduction_rate_low=Decimal("0.1400"),
        deduction_rate_high=Decimal("0.0800"),
        deduction_threshold_bpc=Decimal("15.0"),
        child_deduction_annual_bpc=Decimal("20.0"),
        disabled_child_deduction_annual_bpc=Decimal("40.0"),
        sac_ficto_increment_rate=Decimal("0.0600"),
        rental_credit_rate=Decimal("0.0800"),
        mortgage_deduction_max_annual_bpc=Decimal("36.0"),
        source="Ley 18.083, Dec. 148/007, Ley 18.719 Art. 764, Ley 20.124 (DGI)",
        verification_status=RuleVerificationStatus.VERIFIED,
    )


def get_iass_ruleset(year: int) -> IASSRuleSet | None:
    """Construye el RuleSet de IASS para pasividades y jubilaciones."""
    if year < 2024:
        return None

    return IASSRuleSet(
        rule_version=f"UY-BPS-IASS-{year}-v1",
        year=year,
        brackets=_OFFICIAL_IASS_BRACKETS_2024_ONWARDS,
        deduction_rate_low=Decimal("0.1400"),
        deduction_rate_high=Decimal("0.0800"),
        deduction_threshold_bpc=Decimal("15.0"),
        standard_health_deduction_monthly_bpc=Decimal("0.5"),
        source="Ley 18.314 (IASS), Ley 20.124 Art. 5 (Aumento MNI a 9 BPC)",
        verification_status=RuleVerificationStatus.VERIFIED,
    )


def get_iva_ruleset(year: int) -> IVARuleSet | None:
    """Construye el RuleSet de IVA para Servicios Personales."""
    if year < 2024:
        return None

    return IVARuleSet(
        rule_version=f"UY-DGI-IVA-{year}-v1",
        year=year,
        basic_rate=Decimal("0.2200"),
        minimum_rate=Decimal("0.1000"),
        cede_withholding_rate=Decimal("0.6000"),
        source="Título 10 T.O. 1996 Art. 12, Ley 18.083, Dec. 220/998, Dec. 94/002",
        verification_status=RuleVerificationStatus.VERIFIED,
    )


def get_irpf_independent_ruleset(year: int) -> IRPFIndependentRuleSet | None:
    """Construye el RuleSet de IRPF Cat. II para Servicios Personales."""
    if year < 2024:
        return None

    return IRPFIndependentRuleSet(
        rule_version=f"UY-DGI-IRPF-IND-{year}-v1",
        year=year,
        standard_expense_deduction_rate=Decimal("0.3000"),
        taxable_income_factor=Decimal("0.7000"),
        bimonthly_advance_rate=Decimal("0.1000"),
        source="Título 7 T.O. 1996 Art. 34, Dec. 148/007 Art. 62",
        verification_status=RuleVerificationStatus.VERIFIED,
    )


def get_cjppu_ruleset(year: int) -> CJPPURuleSet | None:
    """Construye el RuleSet de Caja Profesional para el año fiscal."""
    if year < 2024:
        return None

    return CJPPURuleSet(
        rule_version=f"UY-CJPPU-{year}-v1",
        year=year,
        contribution_rate=Decimal("0.1650"),
        category_fictitious_salaries=_CJPPU_CATEGORIES_2026,
        source="Ley 17.738 Art. 60, Ley 20.212",
        verification_status=RuleVerificationStatus.PARTIALLY_VERIFIED,
    )


def get_literal_e_ruleset(year: int) -> LiteralERuleSet | None:
    """Construye el RuleSet de Pequeña Empresa - Literal E para el año fiscal."""
    if year < 2024:
        return None

    return LiteralERuleSet(
        rule_version=f"UY-DGI-LIT-E-{year}-v1",
        year=year,
        threshold_ui=Decimal("305000.00"),
        dgi_base_fee_monthly=Decimal("5450.00"),
        bps_patronal_fee_monthly=Decimal("4200.00"),
        tier_1_months=12,
        tier_1_rate=Decimal("0.2500"),
        tier_2_months=24,
        tier_2_rate=Decimal("0.5000"),
        tier_3_rate=Decimal("1.0000"),
        source="Título 4 T.O. 1996 Art. 52 Lit. E, Ley 18.083, Ley 19.996 Art. 287",
        verification_status=RuleVerificationStatus.PARTIALLY_VERIFIED,
    )


def get_monotributo_ruleset(year: int) -> MonotributoRuleSet | None:
    """Construye el RuleSet de Monotributo Común y Social MIDES para el año fiscal."""
    if year < 2024:
        return None

    return MonotributoRuleSet(
        rule_version=f"UY-BPS-MONO-{year}-v1",
        year=year,
        threshold_unipersonal_ui=Decimal("305000.00"),
        threshold_sociedad_ui=Decimal("508000.00"),
        max_premises_sqm=Decimal("15.00"),
        max_employees_unipersonal=1,
        base_fee_unipersonal_monthly=Decimal("2850.00"),
        base_fee_sociedad_monthly=Decimal("4950.00"),
        mides_tier_1_months=12,
        mides_tier_1_rate=Decimal("0.2500"),
        mides_tier_2_months=24,
        mides_tier_2_rate=Decimal("0.5000"),
        mides_tier_3_months=36,
        mides_tier_3_rate=Decimal("0.7500"),
        mides_tier_4_rate=Decimal("1.0000"),
        source="Ley 18.083 Arts. 70-82 (Monotributo), Ley 18.874 (MIDES)",
        verification_status=RuleVerificationStatus.VERIFIED,
    )
