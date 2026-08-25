"""
Enums para el subdominio laboral, previsional y tributario uruguayo.
"""

from enum import StrEnum


class FinanceMode(StrEnum):
    """Modo de experiencia financiera de la familia."""

    BASIC = "basic"  # Modo Rápido (Default)
    CONTADOR_ORIENTAL = "contador_pro"  # Modo Contador Oriental Pro


class ActivityNature(StrEnum):
    """Naturaleza de la actividad económica o relación laboral."""

    DEPENDIENTE = "dependiente"  # Empleados comercio, industria, servicios, etc.
    INDEPENDIENTE = "independiente"  # Servicios personales, Literal E, Monotributo
    PASIVIDAD = "pasividad"  # Jubilaciones y pensiones
    TRANSFERENCIA_SOCIAL = "social_transfer"  # Asignaciones familiares, subsidios


class RemunerationType(StrEnum):
    """Tipo de remuneración de un trabajador dependiente."""

    MENSUAL = "mensual"
    JORNALERO = "jornalero"


class IncomeConcept(StrEnum):
    """Concepto financiero / laboral del ingreso percibido."""

    SALARY = "salary"  # Sueldo mensual habitual / Jornal
    AGUINALDO = "aguinaldo"  # Sueldo Anual Complementario cobrado
    SALARIO_VACACIONAL = "vacation_pay"  # Salario vacacional cobrado
    OVERTIME = "overtime"  # Horas extras computables
    COMMISSION = "commission"  # Comisiones computables
    BONUS = "bonus"  # Bonificaciones / Gratificaciones
    OTHER = "other"  # Otros ingresos
    HONORARIOS = "honorarios"  # Honorarios profesionales / servicios


class CalculationStatus(StrEnum):
    """Estado del resultado del cálculo laboral."""

    CALCULATED = "calculated"  # Cálculo exacto con meses reales completos
    PROVISIONAL = "provisional"  # Cálculo estimado con meses futuros
    INSUFFICIENT_DATA = "insufficient_data"  # Faltan datos obligatorios
    REQUIRES_REVIEW = "requires_review"  # Caso no estándar o sin clasificar


class FonasaBeneficiaryType(StrEnum):
    """Composición familiar del trabajador para la alícuota FONASA (Ley 18.211)."""

    SINGLE_NO_CHILDREN = "single_no_children"  # Sin hijos, sin cónyuge
    WITH_CHILDREN_NO_SPOUSE = (
        "with_children_no_spouse"  # Con hijos menores/discapacidad, sin cónyuge
    )
    NO_CHILDREN_WITH_SPOUSE = "no_children_with_spouse"  # Sin hijos, con cónyuge
    WITH_CHILDREN_AND_SPOUSE = "with_children_and_spouse"  # Con hijos y cónyuge


class RuleVerificationStatus(StrEnum):
    """Estado de verificación oficial de la regla tributaria/previsional."""

    VERIFIED = "verified"  # Cotejado contra decreto u ordenanza oficial
    PARTIALLY_VERIFIED = "partially_verified"  # Norma y fórmula verificadas
    PENDING_OFFICIAL_PUBLICATION = (
        "pending_publication"  # Aún no decretado oficialmente
    )


class EstimationAccuracy(StrEnum):
    """Nivel de convergencia y exactitud del cálculo inverso."""

    EXACT = "exact"  # Diferencia absoluta = 0.00
    WITHIN_TOLERANCE = "within_tolerance"  # Diferencia <= tolerancia (0.01)
    REQUIRES_REVIEW = "requires_review"  # No convergió o fuera de rango


class CalculationMode(StrEnum):
    """Modalidad de cómputo solicitada al motor."""

    MONTHLY_WITHHOLDING_SIMULATION = (
        "monthly_simulation"  # Simulación recibo dependiente
    )
    ANNUAL_TAX_SETTLEMENT = "annual_settlement"  # Liquidación y ajuste anual IRPF
    AGUINALDO = "aguinaldo"  # Sueldo Anual Complementario (Ley 12.840)
    SALARIO_VACACIONAL = "salario_vacacional"  # Salario Vacacional (Ley 16.101)
    INVERSE_NOMINAL_ESTIMATION = "inverse_estimation"  # Inverso Líquido->Nominal
    PERSONAL_SERVICES_SETTLEMENT = (
        "personal_services_settlement"  # Liquidación Servicios Personales
    )


class IndependentTaxRegime(StrEnum):
    """Régimen tributario de una actividad económica independiente."""

    SERVICIOS_PERSONALES = "servicios_personales"
    LITERAL_E = "literal_e"
    MONOTRIBUTO = "monotributo"
    MONOTRIBUTO_MIDES = "monotributo_mides"


class PensionFundType(StrEnum):
    """Caja u organismo de previsión social."""

    BPS = "bps"
    CJPPU = "cjppu"
    CAJA_NOTARIAL = "caja_notarial"
    CAJA_BANCARIA = "caja_bancaria"
    MILITAR = "militar"
    POLICIAL = "policial"


class EligibilityStatus(StrEnum):
    """Estado de evaluación de elegibilidad de un régimen tributario."""

    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    REQUIRES_REVIEW = "requires_review"
