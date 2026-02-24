"""
Formatters centralizados para el Contador Oriental
Evita duplicación de formateo de moneda y otros valores
"""

from __future__ import annotations


def format_currency(value: float) -> str:
    """
    Formatear moneda uruguaya de forma consistente.
    
    Args:
        value: Valor numérico a formatear
        
    Returns:
        String formateado como pesos uruguayos (ej: "80.000")
        
    Examples:
        >>> format_currency(80000)
        '80.000'
        >>> format_currency(1234.5)
        '1.235'
    """
    return f"{value:,.0f}".replace(",", ".")


def format_currency_with_symbol(value: float) -> str:
    """
    Formatear moneda uruguaya con símbolo $.
    
    Args:
        value: Valor numérico a formatear
        
    Returns:
        String con símbolo $ (ej: "$ 80.000")
        
    Examples:
        >>> format_currency_with_symbol(80000)
        '$ 80.000'
    """
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
