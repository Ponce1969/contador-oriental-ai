"""
Constantes de diseño responsivo centralizadas.
Evita redefinir breakpoints y columnas en cada view.
"""

from __future__ import annotations


class Responsive:
    COL_FULL: dict[str, int] = {"xs": 12}
    COL_HALF: dict[str, int] = {"xs": 12, "sm": 6}
    COL_THIRD: dict[str, int] = {"xs": 12, "sm": 4}
    COL_TWO_THIRDS: dict[str, int] = {"xs": 12, "sm": 8}

    MOBILE_BREAKPOINT = 600
    TABLET_BREAKPOINT = 1024
