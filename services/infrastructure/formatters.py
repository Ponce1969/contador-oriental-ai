"""
Formateo de moneda uruguaya.
En Uruguay los centésimos son obsoletos para contabilidad familiar.
Usa Decimal para precisión financiera exacta.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def format_pesos(monto: Decimal) -> str:
    """
    Formatear monto en pesos uruguayos sin decimales.

    >>> format_pesos(Decimal("18480.00"))
    '$ 18.480'
    >>> format_pesos(12990)
    '$ 12.990'
    >>> format_pesos(Decimal("770.50"))
    '$ 771'
    """
    if not isinstance(monto, Decimal):
        monto = Decimal(str(monto))
    entero = int(monto.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    entero_str = f"{entero:,}".replace(",", ".")
    return f"$ {entero_str}"


def format_pesos_ai(monto: Decimal) -> str:
    """
    Formatear monto para prompts de IA: SIN separador de miles.

    Las IAs (Gemma2, Llama3) no necesitan separadores y pueden
    malinterpretarlos:
    - Llama3 trunca en el espacio: "$ 560 620" → lee "$ 560"
    - Gemma2 confunde el punto con decimal: "$ 173.720" → lee "173 con 720"
    
    Sin separador: "$ 560620" es inequívoco para cualquier modelo.

    >>> format_pesos_ai(Decimal("173720"))
    '$ 173720'
    >>> format_pesos_ai(Decimal("18480"))
    '$ 18480'
    >>> format_pesos_ai(Decimal("650"))
    '$ 650'
    """
    if not isinstance(monto, Decimal):
        monto = Decimal(str(monto))
    entero = int(monto.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return f"$ {entero}"


def format_cotizacion(rate: Decimal) -> str:
    """
    Formatear cotización de dólar con 2 decimales y separador de miles.

    Para cotizaciones como USD/UYU necesitamos decimales (40.01),
    a diferencia de pesos uruguayos que se redondean al entero.

    >>> format_cotizacion(Decimal("40.0100"))
    '$ 40.01'
    >>> format_cotizacion(Decimal("42.5"))
    '$ 42.50'
    >>> format_cotizacion(Decimal("1234.5678"))
    '$ 1.234,57'
    """
    if not isinstance(rate, Decimal):
        rate = Decimal(str(rate))
    # Quantize a 2 decimales con redondeo banker's
    rate_2d = rate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    # Formatear: parte entera con punto, parte decimal con coma
    entero = int(rate_2d)
    decimal_part = int((rate_2d - entero) * 100)
    entero_str = f"{entero:,}".replace(",", ".")
    return f"$ {entero_str},{decimal_part:02d}"


def pesos_entero(monto: Decimal) -> int:
    """Redondear al entero más cercano para guardar/comparar."""
    if not isinstance(monto, Decimal):
        monto = Decimal(str(monto))
    return int(monto.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
