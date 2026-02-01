"""
Type stubs para Flet - Correcciones para los type hints del framework Flet.

Este archivo proporciona correcciones para los stubs de tipos de Flet que
actualmente tienen bugs. El type checker 'ty' reporta errores falsos positivos
debido a definiciones incorrectas en los stubs de Flet.

Uso: Agregar 'type: ignore' comentarios donde sea necesario, o usar este módulo
para proporcionar type hints correctos cuando sea posible.
"""

from typing import Any

# Flet tiene stubs incorrectos para:
# - ft.Text: El primer parámetro debería aceptar str (value), pero el stub
#   dice int|float
# - ft.Icon: El parámetro 'icon' es opcional en la implementación pero
#   requerido en el stub
# - Page.banner: Existe pero no está en los stubs
# - Page.window_icon: Existe pero no está en los stubs
# - Page.snack_bar: Existe pero no está en los stubs

# Solución recomendada: Usar type: ignore


def cast_flet_text_value(value: str) -> Any:
    """
    Cast para el valor de ft.Text.
    Flet stubs dice que el primer parámetro es int|float|None, pero acepta str.
    """
    return value


def cast_icon_data(icon: Any) -> Any:
    """
    Cast para ft.Icon data.
    Flet stubs requiere parámetro 'icon' pero la implementación no.
    """
    return icon
