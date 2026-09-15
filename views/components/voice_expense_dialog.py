"""Component for recording and extracting expenses via voice in Flet."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING

import flet as ft
import httpx

if TYPE_CHECKING:
    from flet import Page

logger = logging.getLogger(__name__)

_VOICE_INTERNAL = os.getenv("VOICE_API_URL", "http://voice_api:8553")
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
        base_url = _VOICE_PUBLIC.rstrip("/")
        upload_url = (
            f"{base_url}/voice-upload-form"
            f"?session_id={session_id}&familia_id={familia_id}"
        )

        # Controls
        status_text = ft.Text(
            "Tocá el botón para abrir la grabadora y dictar tu gasto.",
            size=13,
            color=ft.Colors.GREY_700,
            text_align=ft.TextAlign.CENTER,
        )
        spinner = ft.ProgressRing(width=28, height=28, stroke_width=3, visible=False)
        polling_active = True

        async def _poll_result():
            interval = 1.5
            max_attempts = 80  # 120 seconds total
            for _ in range(max_attempts):
                if not polling_active:
                    return
                await asyncio.sleep(interval)
                if not polling_active:
                    return

                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        resp = await client.get(
                            f"{_VOICE_INTERNAL}/voice-resultado/{session_id}"
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            if data.get("status") == "processing":
                                spinner.visible = True
                                status_text.value = (
                                    "Audio recibido 🎙️ Transcribiendo con IA local..."
                                )
                                status_text.color = ft.Colors.BLUE_700
                                if hasattr(page, "update"):
                                    page.update()

                            if data.get("ready"):
                                _close_dialog()
                                if data.get("success"):
                                    on_expense_parsed(data)
                                else:
                                    err_msg = data.get(
                                        "error", "No se pudo interpretar el audio"
                                    )
                                    page.overlay.append(
                                        ft.SnackBar(ft.Text(f"❌ {err_msg}"), open=True)
                                    )
                                    page.update()
                                return
                except Exception as ex:
                    logger.debug("[VOICE_DIALOG] Polling error: %s", ex)

        # Schedule polling task safely via page.run_task (or active event loop)
        if hasattr(page, "run_task"):
            page.run_task(_poll_result)
        else:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_poll_result())
            except RuntimeError:
                logger.debug("[VOICE_DIALOG] No running event loop detected")

        def _close_dialog(_=None):
            nonlocal polling_active
            polling_active = False
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
                            style=ft.ButtonStyle(
                                padding=ft.Padding.symmetric(horizontal=16, vertical=12)
                            ),
                        ),
                        ft.Container(height=6),
                        ft.Row(
                            controls=[spinner, status_text],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=12,
                        ),
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
