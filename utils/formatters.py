"""
Formatters centralizados para el Contador Oriental
Evita duplicación de formateo de moneda y otros valores
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

_CURRENCIES_SUPPORTED = {"UYU", "USD"}


def _format_uyu(value: float | Decimal) -> str:
    """Formatear monto en pesos uruguayos: entero con separador de miles."""
    if isinstance(value, Decimal):
        value = int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return f"{value:,.0f}".replace(",", ".")


def _format_usd(value: float | Decimal) -> str:
    """Formatear monto en dólares: 2 decimales con separador de miles."""
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    value = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sign = "-" if value < 0 else ""
    value = abs(value)
    entero = int(value)
    decimal_part = int((value - entero) * 100)
    entero_str = f"{entero:,}".replace(",", ".")
    return f"{sign}{entero_str},{decimal_part:02d}"


def format_currency(value: float | Decimal, currency: str = "UYU") -> str:
    """
    Formatear monto según la moneda.

    Public contract: value should be Decimal. Float support is retained
    temporarily during the migration window; callers will be migrated to
    Decimal in task 4.2.
    """
    currency = currency.upper()
    if currency == "UYU":
        return _format_uyu(value)
    if currency == "USD":
        return _format_usd(value)
    raise ValueError(f"Moneda no soportada: {currency}")


def format_currency_with_symbol(value: float | Decimal, currency: str = "UYU") -> str:
    """Formatear moneda con símbolo ($ para UYU, USD para dólares)."""
    number = format_currency(value, currency=currency)
    if currency.upper() == "USD":
        return f"USD {number}"
    return f"$ {number}"


def format_percentage(value: float) -> str:
    """
    Formatear porcentaje con 1 decimal.

    Args:
        value: Valor decimal (0.85 para 85%)

    Returns:
        String con % (ej: "85.0%")

    Examples:
        >>> format_percentage(0.8567)
        '85.7%'
    """
    return f"{value * 100:.1f}%"
