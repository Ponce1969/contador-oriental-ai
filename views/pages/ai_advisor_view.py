"""
Vista de chat con el Contador Oriental
"""

from __future__ import annotations

import asyncio
from datetime import datetime

import flet as ft
from result import Err, Ok

from controllers.ai_controller import AIController
from core.session import SessionManager
from core.state import AppState
from flet_types.flet_types import CorrectSnackBar
from models.ai_model import ChatMessage
from services.report_service import ReportService
from views.layouts.main_layout import MainLayout


class AIAdvisorView:
    """Vista de chat con el Contador Oriental"""

    def __init__(self, page: ft.Page, router):
        self.page = page
        self.router = router

        if not SessionManager.is_logged_in(page):
            router.navigate("/login")
            return

        familia_id = SessionManager.get_familia_id(page)
        self.controller = AIController(familia_id=familia_id)
        self.report_service = ReportService()
        self.chat_history: list[ChatMessage] = []
        self._last_respuesta: str = ""
        self._familia_nombre: str = (
            SessionManager.get_username(page) or "Familia"
        )

        # Campo de pregunta moderno
        self.pregunta_input = ft.TextField(
            hint_text="Escribí tu consulta financiera...",
            multiline=True,
            min_lines=1,
            max_lines=3,
            expand=True,
            border_radius=25,
            bgcolor=ft.Colors.WHITE,
            content_padding=ft.padding.symmetric(horizontal=20, vertical=14),
            border_color=ft.Colors.GREY_300,
            on_submit=self._handle_submit,
        )

        # Checkbox para incluir gastos
        self.incluir_gastos_checkbox = ft.Checkbox(
            label="Incluir mis gastos del mes",
            value=True,
        )

        # Columna de chat
        self.chat_column = ft.Column(
            spacing=15,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        # Typing indicator: tres puntos animados
        self._dot1 = ft.Text("•", size=28, color=ft.Colors.BLUE_700, opacity=1)
        self._dot2 = ft.Text("•", size=28, color=ft.Colors.BLUE_700, opacity=0.4)
        self._dot3 = ft.Text("•", size=28, color=ft.Colors.BLUE_700, opacity=0.1)
        self.typing_indicator = ft.Container(
            content=ft.Row(
                controls=[self._dot1, self._dot2, self._dot3],
                spacing=4,
            ),
            visible=False,
            padding=ft.padding.only(left=16),
        )

        # Botón ver informe (oculto hasta recibir respuesta)
        self.pdf_button = ft.IconButton(
            icon=ft.Icons.ASSIGNMENT_ROUNDED,
            icon_color=ft.Colors.BLUE_700,
            tooltip="Ver informe formal",
            visible=False,
            on_click=lambda e: self.page.run_task(self._exportar_pdf),  # type: ignore
        )

        # Quick chips
        self.quick_chips = ft.Row(
            wrap=True,
            spacing=8,
            controls=[
                self._create_chip(
                    "¿Cómo ahorrar IVA?", ft.Icons.ACCOUNT_BALANCE_WALLET
                ),
                self._create_chip("¿Débito o Crédito?", ft.Icons.CREDIT_CARD),
                self._create_chip("Deducir Alquiler", ft.Icons.HOME),
                self._create_chip("Resumen de Gastos", ft.Icons.ANALYTICS),
            ],
        )

    def _create_chip(self, text: str, icon_data: ft.IconData) -> ft.Chip:
        return ft.Chip(
            label=ft.Text(text, size=12),
            leading=ft.Icon(icon_data, size=16),
            on_click=lambda e, t=text: self.page.run_task(
                self._send_quick_question, t
            ),
            bgcolor=ft.Colors.GREEN_50,
        )

    async def _animate_typing(self) -> None:
        """Animación cíclica de opacidad para los tres puntos (efecto onda)"""
        dots = self.typing_indicator.content.controls  # type: ignore[union-attr]
        for i, dot in enumerate(dots):
            dot.opacity = 0.3 + (i * 0.2)

        while self.typing_indicator.visible:
            for dot in dots:
                dot.opacity = 1.0 if dot.opacity < 0.5 else 0.3
            self.page.update()
            await asyncio.sleep(0.4)

    async def _handle_submit(self, e) -> None:
        """Puente para on_submit del TextField y on_click del IconButton"""
        await self._on_consultar(e)

    async def _send_quick_question(self, text: str) -> None:
        self.pregunta_input.value = text
        self.page.update()
        await self._on_consultar(None)

    def render(self):
        """Layout principal"""
        self._agregar_mensaje_bienvenida()
        is_mobile = AppState.device == "mobile"

        return MainLayout(
            page=self.page,
            router=self.router,
            content=ft.Column(
                controls=[
                    # Encabezado
                    ft.Row(
                        controls=[
                            ft.Text(
                                "🇺🇾 Contador Oriental",
                                size=20 if is_mobile else 26,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Column(
                                controls=[
                                    ft.Container(
                                        content=ft.Text(
                                            "IA LOCAL",
                                            size=9 if is_mobile else 10,
                                            color=ft.Colors.WHITE,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        bgcolor=ft.Colors.GREEN_600,
                                        padding=ft.padding.symmetric(
                                            horizontal=8 if is_mobile else 10,
                                            vertical=3 if is_mobile else 4,
                                        ),
                                        border_radius=10,
                                    ),
                                    self.pdf_button,
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.END,
                                spacing=2,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Text(
                        "Asesoría basada en leyes uruguayas y tus gastos reales.",
                        color=ft.Colors.GREY_600,
                        size=11 if is_mobile else 13,
                    ),

                    # Área de chat
                    ft.Container(
                        content=self.chat_column,
                        bgcolor=ft.Colors.GREY_50,
                        border_radius=16 if is_mobile else 20,
                        padding=12 if is_mobile else 20,
                        expand=True,
                        border=ft.border.all(1, ft.Colors.GREY_200),
                    ),

                    # Typing indicator
                    self.typing_indicator,

                    # Chips + input + botón enviar
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                self.quick_chips,
                                ft.Row(
                                    controls=[
                                        self.pregunta_input,
                                        ft.IconButton(
                                            icon=ft.Icons.SEND_ROUNDED,
                                            icon_color=ft.Colors.WHITE,
                                            bgcolor=ft.Colors.BLUE_700,
                                            icon_size=20 if is_mobile else 22,
                                            on_click=self._handle_submit,
                                            tooltip="Enviar consulta",
                                        ),
                                    ],
                                    spacing=8,
                                    vertical_alignment=ft.CrossAxisAlignment.END,
                                ),
                                ft.Container(
                                    content=self.incluir_gastos_checkbox,
                                    padding=ft.padding.only(left=6 if is_mobile else 10),
                                ),
                            ],
                            spacing=8 if is_mobile else 10,
                        ),
                        padding=ft.padding.symmetric(
                            horizontal=2 if is_mobile else 4,
                            vertical=6 if is_mobile else 8,
                        ),
                    ),
                ],
                spacing=10 if is_mobile else 16,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
        )

    def _agregar_mensaje_bienvenida(self) -> None:
        self.chat_history.append(ChatMessage(
            role="assistant",
            content=(
                "¡Hola! Soy el **Contador Oriental**, tu asesor contable.\n\n"
                "Puedo ayudarte con:\n"
                "- 💳 Beneficios de débito/crédito (Inclusión Financiera)\n"
                "- 🏠 Deducciones de IRPF (alquiler, hijos, hipoteca)\n"
                "- 💰 Ahorro en UI contra la inflación\n"
                "- 📊 Análisis de tus gastos del mes\n\n"
                "Usá los botones de acceso rápido o escribí tu consulta."
            ),
        ))
        self._render_chat()

    async def _on_consultar(self, e) -> None:
        """Manejar consulta al contador (async: no bloquea la UI)"""
        if not self.pregunta_input.value or not self.pregunta_input.value.strip():
            self._show_error("Por favor escribí una pregunta")
            return

        pregunta = self.pregunta_input.value.strip()

        self.chat_history.append(ChatMessage(role="user", content=pregunta))
        self._render_chat()

        self.pregunta_input.value = ""
        self.pregunta_input.disabled = True
        self.typing_indicator.visible = True
        self.page.update()

        asyncio.create_task(self._animate_typing())

        incluir_gastos = self.incluir_gastos_checkbox.value or False

        result = await self.controller.consultar_contador(
            pregunta=pregunta,
            incluir_gastos=incluir_gastos,
        )

        self.typing_indicator.visible = False

        match result:
            case Ok(response):
                self._last_respuesta = response.respuesta
                self.pdf_button.visible = True
                self.chat_history.append(
                    ChatMessage(role="assistant", content=response.respuesta)
                )
            case Err(error):
                self.chat_history.append(
                    ChatMessage(
                        role="assistant",
                        content=f"❌ Error: {error.message}",
                    )
                )
                self._show_error(error.message)

        self.pregunta_input.disabled = False
        self._render_chat()
        self.page.update()

    def _render_chat(self) -> None:
        """Renderizado premium con Markdown y anchos controlados"""
        self.chat_column.controls.clear()

        for mensaje in self.chat_history:
            is_user = mensaje.role == "user"

            bubble = ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(
                                    ft.Icons.PERSON if is_user
                                    else ft.Icons.AUTO_AWESOME,
                                    size=12,
                                    color=ft.Colors.BLUE_GREY_400,
                                ),
                                ft.Text(
                                    "TÚ" if is_user else "CONTADOR ORIENTAL",
                                    size=10,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.BLUE_GREY_400,
                                ),
                            ],
                            spacing=5,
                        ),
                        ft.Markdown(
                            value=mensaje.content,
                            selectable=True,
                            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                            on_tap_link=lambda e: self.page.launch_url(e.data),
                        ),
                    ],
                    spacing=8,
                    tight=True,
                ),
                padding=15,
                bgcolor=ft.Colors.BLUE_50 if is_user else ft.Colors.WHITE,
                border=ft.border.all(
                    1,
                    ft.Colors.BLUE_100 if is_user else ft.Colors.GREY_200,
                ),
                border_radius=ft.border_radius.only(
                    top_left=15,
                    top_right=15,
                    bottom_left=15 if is_user else 2,
                    bottom_right=2 if is_user else 15,
                ),
                width=None if AppState.device == "mobile" else 500,
                shadow=ft.BoxShadow(
                    blur_radius=5,
                    color=ft.Colors.with_opacity(0.05, ft.Colors.BLACK),
                    offset=ft.Offset(0, 2),
                ),
            )

            self.chat_column.controls.append(
                ft.Row(
                    controls=[bubble],
                    alignment=(
                        ft.MainAxisAlignment.END if is_user
                        else ft.MainAxisAlignment.START
                    ),
                )
            )

        self.page.update()
        self.chat_column.scroll_to(offset=-1, duration=400)

    async def _exportar_pdf(self) -> None:
        """Muestra el informe en un modal con opción de copiar al portapapeles."""
        if not self._last_respuesta:
            return

        fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
        reporte = (
            f"## INFORME CONTABLE - AUDITOR FAMILIAR\n"
            f"**Familia:** {self._familia_nombre}  "
            f"**Fecha:** {fecha}\n\n"
            f"**Consulta:** {self.controller.last_pregunta}\n\n"
            f"---\n\n"
            f"{self._last_respuesta}\n\n"
            f"---\n"
            f"*Generado por el Contador Oriental · Auditor Familiar*"
        )

        def copiar(e: object) -> None:
            self.page.set_clipboard(reporte)
            self.page.snack_bar = CorrectSnackBar(
                content=ft.Text("✅ Copiado al portapapeles"),
                open=True,
            )
            self.page.update()

        def cerrar(e: object) -> None:
            dlg.open = False
            self.page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.DESCRIPTION, color=ft.Colors.BLUE_700),
                    ft.Text("Informe del Contador Oriental"),
                ],
                spacing=10,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Markdown(
                            reporte,
                            selectable=True,
                            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                        )
                    ],
                    scroll=ft.ScrollMode.AUTO,
                    tight=True,
                ),
                width=600,
                height=420,
            ),
            actions=[
                ft.ElevatedButton(
                    "Copiar texto",
                    icon=ft.Icons.COPY,
                    on_click=copiar,
                ),
                ft.TextButton("Cerrar", on_click=cerrar),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            open=True,
        )

        self.page.overlay.append(dlg)
        self.page.update()

    def _show_error(self, msg: str) -> None:
        self.page.snack_bar = CorrectSnackBar(
            content=ft.Text(f"❌ {msg}"),
            open=True,
        )
        self.page.update()
