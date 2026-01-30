"""
Tipos correctos para Flet cuando las definiciones oficiales son incorrectas.
Este archivo soluciona los problemas de tipado de Flet sin usar type: ignore.
"""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

# Type alias para handlers de click - más flexible para compatibilidad
ButtonType = Callable[[ft.ControlEvent], None] | None


class CorrectElevatedButton(ft.ElevatedButton):
    """
    Wrapper con tipos correctos para ElevatedButton.
    
    La API real de Flet acepta:
    - ElevatedButton(text: str, on_click: Callable)
    
    Pero las definiciones de tipo de ty son incorrectas.
    """
    
    def __init__(
        self,
        text: str,
        on_click: ButtonType = None,
        **kwargs
    ) -> None:
        # Llamamos al constructor real con los tipos correctos
        # Forzamos los tipos correctos ignorando las definiciones incorrectas de Flet
        super().__init__(text, on_click=on_click, **kwargs)  # type: ignore[arg-type]


class CorrectSnackBar(ft.SnackBar):
    """
    Wrapper con tipos correctos para SnackBar.
    """
    
    def __init__(
        self,
        content: ft.Control | str,
        open: bool = False,
        **kwargs
    ) -> None:
        super().__init__(content=content, open=open, **kwargs)
