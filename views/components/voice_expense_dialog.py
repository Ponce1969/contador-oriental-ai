"""Component for recording and extracting expenses via voice in Flet."""

from __future__ import annotations

import logging
import os
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING

import flet as ft

if TYPE_CHECKING:
    from flet import Page

from core.session import SessionManager

logger = logging.getLogger(__name__)

_VOICE_PUBLIC = os.getenv("VOICE_API_PUBLIC_URL", "/voice")


class VoiceExpenseDialog:
    """Dialog that coordinates audio recording and async polling with voice_api."""

    @classmethod
    def show(
        cls,
        page: Page,
        on_expense_parsed: Callable[[dict], None],
        familia_id: int = 1,
    ) -> None:
        session_id = str(uuid.uuid4())
        # Preservar autenticación al volver de la grabadora móvil/web
        SessionManager.register_voice_session(session_id, page)
        base_url = _VOICE_PUBLIC.rstrip("/")
        upload_url = (
            f"{base_url}/voice-upload-form"
            f"?session_id={session_id}&familia_id={familia_id}"
        )

        def _close_dialog(_=None):
            dialog.open = False
            if hasattr(page, "update"):
                try:
                    page.update()
                except Exception:
                    pass

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.MIC_ROUNDED, color=ft.Colors.BLUE_600, size=24),
                    ft.Text(
                        "Dictar Gasto por Voz",
                        weight=ft.FontWeight.BOLD,
                        size=18,
                    ),
                ],
                spacing=10,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Text(
                                        "💬 Ejemplos de dictado:",
                                        weight=ft.FontWeight.BOLD,
                                        size=12,
                                        color=ft.Colors.BLUE_900,
                                    ),
                                    ft.Text(
                                        "• '450 pesos en el Disco con Santander'\n"
                                        "• 'Dos lucas de nafta en Ancap'\n"
                                        "• 'Mil doscientos en Farmashop'",
                                        size=12,
                                        color=ft.Colors.BLUE_800,
                                    ),
                                ],
                                spacing=4,
                            ),
                            bgcolor=ft.Colors.BLUE_50,
                            padding=12,
                            border_radius=8,
                            border=ft.Border.all(1, ft.Colors.BLUE_200),
                        ),
                        ft.Container(height=10),
                        ft.Button(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.MIC),
                                    ft.Text("Abrir grabadora de voz"),
                                ],
                                spacing=8,
                                tight=True,
                            ),
                            bgcolor=ft.Colors.BLUE_600,
                            color=ft.Colors.WHITE,
                            url=ft.Url(upload_url, target=ft.UrlTarget.SELF),
                            on_click=_close_dialog,
                            style=ft.ButtonStyle(
                                padding=ft.Padding.symmetric(horizontal=16, vertical=12)
                            ),
                        ),
                        ft.Container(height=4),
                    ],
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True,
                ),
                width=420,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=_close_dialog),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.overlay.append(dialog)
        dialog.open = True
        page.update()
