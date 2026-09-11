"""
Gestor de DatePicker para Flet, evitando fugas y duplicados en page.overlay.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

import flet as ft


class DatePickerManager:
    """Gestiona instancias de ft.DatePicker limpiando page.overlay para evitar fugas."""

    @staticmethod
    def open_date_picker(
        page: ft.Page,
        current_date: date,
        on_selected: Callable[[date], None],
    ) -> None:
        # Remover DatePickers previos en overlay para evitar acumulación
        page.overlay[:] = [
            ctrl for ctrl in page.overlay if not isinstance(ctrl, ft.DatePicker)
        ]

        def _handle_change(e: ft.ControlEvent) -> None:
            if dp.value:
                val: Any = dp.value
                if hasattr(val, "date"):
                    selected = val.date()
                elif isinstance(val, date):
                    selected = val
                else:
                    try:
                        selected = date.fromisoformat(str(val).split("T")[0])
                    except Exception:
                        selected = current_date
                on_selected(selected)

        dp = ft.DatePicker(
            value=current_date,
            confirm_text="Aceptar",
            cancel_text="Cancelar",
            on_change=_handle_change,
        )
        page.overlay.append(dp)
        dp.open = True
        page.update()
