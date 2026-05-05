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
    Formatear monto para prompts de IA: usa ESPACIO como separador de miles.

    Llama/Gemma confunden el punto como separador decimal (formato inglés),
    interpretando "$ 173.720" como "ciento setenta y tres con setecientos
    veinte centesimos". Con espacio: "$ 173 720" es inequivoco.

    >>> format_pesos_ai(Decimal("173720"))
    '$ 173 720'
    >>> format_pesos_ai(Decimal("18480"))
    '$ 18 480'
    >>> format_pesos_ai(Decimal("650"))
    '$ 650'
    """
    if not isinstance(monto, Decimal):
        monto = Decimal(str(monto))
    entero = int(monto.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    entero_str = f"{entero:,}".replace(",", " ")
    return f"$ {entero_str}"


def pesos_entero(monto: Decimal) -> int:
    """Redondear al entero más cercano para guardar/comparar."""
    if not isinstance(monto, Decimal):
        monto = Decimal(str(monto))
    return int(monto.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
