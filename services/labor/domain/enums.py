"""
Enums para el subdominio laboral y de actividades económicas.
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


class CalculationStatus(StrEnum):
    """Estado del resultado del cálculo laboral."""

    CALCULATED = "calculated"  # Cálculo exacto con meses reales completos
    PROVISIONAL = "provisional"  # Cálculo estimado con meses futuros
    INSUFFICIENT_DATA = "insufficient_data"  # Faltan datos obligatorios
    REQUIRES_REVIEW = "requires_review"  # Caso no estándar o sin clasificar
