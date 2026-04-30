"""
Formatters centralizados para el Contador Oriental
Evita duplicación de formateo de moneda y otros valores
"""

from __future__ import annotations

from decimal import Decimal


def format_currency(value: float | Decimal) -> str:
    """
    Formatear moneda uruguaya de forma consistente.
    """
    if isinstance(value, Decimal):
        value = int(value)
    return f"{value:,.0f}".replace(",", ".")


def format_currency_with_symbol(value: float | Decimal) -> str:
    """Formatear moneda uruguaya con simbolo $."""
    return f"$ {format_currency(value)}"


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
