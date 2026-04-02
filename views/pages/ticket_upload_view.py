"""
Vista para carga y confirmación de tickets OCR.
Estados: IDLE → LOADING → CONFIRM → ERROR
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import date
from enum import Enum, auto

import flet as ft
import httpx
from result import Ok

from controllers.expense_controller import ExpenseController
from core.session import SessionManager
from models.categories import ExpenseCategory, PaymentMethod
from models.expense_model import Expense
from models.ticket_model import PartialExpense
from views.layouts.main_layout import MainLayout

# URL interna Docker (Python->microservicio) y publica (browser->microservicio)
_OCR_INTERNAL = os.getenv("OCR_API_URL", "http://ocr_api:8551")
_OCR_PUBLIC = os.getenv("OCR_API_PUBLIC_URL", "http://localhost:8551")

logger = logging.getLogger(__name__)


class _Estado(Enum):
    IDLE = auto()
    LOADING = auto()
    CONFIRM = auto()
    ERROR = auto()


class TicketUploadView:
    """Vista de carga de tickets fotográficos con OCR."""

    def __init__(self, page: ft.Page, router):
        self.page = page
        self.router = router

        if not SessionManager.is_logged_in(page):
            router.navigate("/login")
            return

        familia_id = SessionManager.get_familia_id(page)
        self._familia_id = familia_id
        self.expense_controller = ExpenseController(familia_id=familia_id)

        self._estado = _Estado.IDLE
        self._partial: PartialExpense | None = None
        self._session_id: str | None = None

        # Texto de feedback dinámico durante el procesamiento
        self._loading_text = ft.Text(
            "Preparando...",
            size=18,
            weight=ft.FontWeight.W_500,
        )
        self._loading_sub = ft.Text(
            "",
            size=13,
            color=ft.Colors.GREY_500,
        )

        # Contenedor principal — se reconstruye al cambiar estado
        self._body = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

        self._renderizar()
        asyncio.create_task(self._recuperar_pendiente())

    # ------------------------------------------------------------------
    # Render principal
    # ------------------------------------------------------------------

    def render(self) -> ft.Control:
        return MainLayout(
            page=self.page,
            content=self._body,
            router=self.router,
        )

    def _renderizar(self):
        """Reconstruye el body según el estado actual."""
        self._body.controls.clear()
        if self._estado == _Estado.IDLE:
            self._body.controls.append(self._build_idle())
        elif self._estado == _Estado.LOADING:
            self._body.controls.append(self._build_loading())
        elif self._estado == _Estado.CONFIRM:
            self._body.controls.append(self._build_confirm())
        elif self._estado == _Estado.ERROR:
            self._body.controls.append(self._build_error())
        if hasattr(self.page, "update"):
            self.page.update()

    # ------------------------------------------------------------------
    # Estado IDLE
    # ------------------------------------------------------------------

    def _generar_qr_code(self, url: str, session_id: str) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(
                        "📋 URL del formulario:",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Container(height=8),
                    ft.Container(
                        content=ft.Text(
                            spans=[
                                ft.TextSpan(
                                    url,
                                    style=ft.TextStyle(
                                        size=11,
                                        color=ft.Colors.BLUE_700,
                                        decoration=ft.TextDecoration.UNDERLINE,
                                    ),
                                    url=url,
                                )
                            ]
                        ),
                        padding=10,
                        bgcolor=ft.Colors.BLUE_50,
                        border_radius=8,
                    ),
                ],
            ),
            padding=20,
            border_radius=10,
            bgcolor=ft.Colors.GREY_100,
        )

    def _build_idle(self) -> ft.Control:
        url = self._preparar_sesion()
        asyncio.create_task(self._iniciar_polling(None))

        return ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(height=24),
                ft.Icon(ft.Icons.CAMERA_ALT, size=60, color=ft.Colors.BLUE_400),
                ft.Container(height=8),
                ft.Text(
                    "Cargar ticket de compra",
                    size=22,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Container(height=20),
                ft.Button(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.OPEN_IN_NEW),
                            ft.Text("Abrir formulario en nueva pestaña"),
                        ],
                        spacing=8,
                        tight=True,
                    ),
                    url=ft.Url(url, target=ft.UrlTarget.BLANK),
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.BLUE_600,
                        color=ft.Colors.WHITE,
                    ),
                ),
                ft.Container(height=20),
                ft.Card(
                    content=ft.Container(
                        bgcolor=ft.Colors.AMBER_50,
                        padding=16,
                        content=ft.Column(
                            spacing=8,
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Icon(
                                            ft.Icons.LIGHTBULB,
                                            color=ft.Colors.AMBER_700,
                                            size=20,
                                        ),
                                        ft.Text(
                                            "📋 Cómo funciona",
                                            weight=ft.FontWeight.BOLD,
                                            size=14,
                                            color=ft.Colors.AMBER_900,
                                        ),
                                    ]
                                ),
                                ft.Text(
                                    "1. Tocá el botón — se abre el formulario",
                                    size=12,
                                    color=ft.Colors.GREY_700,
                                ),
                                ft.Text(
                                    "2. Subí la foto del ticket",
                                    size=12,
                                    color=ft.Colors.GREY_700,
                                ),
                                ft.Text(
                                    "3. Esta pantalla avanza sola ✅",
                                    size=12,
                                    color=ft.Colors.GREY_700,
                                ),
                            ],
                        ),
                    ),
                ),
                ft.Container(height=30),
            ],
        )

    # ------------------------------------------------------------------
    # Estado LOADING
    # ------------------------------------------------------------------

    def _build_loading(self) -> ft.Control:
        return ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(height=40),
                ft.ProgressRing(width=60, height=60, stroke_width=4),
                ft.Container(height=16),
                self._loading_text,
                self._loading_sub,
                ft.Container(height=24),
            ],
        )

    # ------------------------------------------------------------------
    # Estado CONFIRM
    # ------------------------------------------------------------------

    def _build_confirm(self) -> ft.Control:
        partial = self._partial
        if partial is None:
            return ft.Text("Error interno")

        # Chip de confianza OCR
        if partial.confianza_ocr >= 0.7:
            conf_color = ft.Colors.GREEN_700
            conf_label = f"Alta confianza ({partial.confianza_ocr:.0%})"
            conf_icon = ft.Icons.CHECK_CIRCLE
        elif partial.confianza_ocr >= 0.4:
            conf_color = ft.Colors.ORANGE_700
            conf_label = f"Confianza media ({partial.confianza_ocr:.0%})"
            conf_icon = ft.Icons.WARNING
        else:
            conf_color = ft.Colors.RED_700
            conf_label = (
                f"Baja confianza ({partial.confianza_ocr:.0%}) — revisá los datos"
            )
            conf_icon = ft.Icons.ERROR

        # Campos pre-llenados editables
        self._monto_field = ft.TextField(
            label="Monto ($)",
            value=str(partial.monto) if partial.monto else "",
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True,
        )
        items_str = ", ".join(partial.items[:3]) if partial.items else ""
        self._descripcion_field = ft.TextField(
            label="Descripción",
            value=partial.comercio or items_str,
            expand=True,
        )
        self._fecha_field = ft.TextField(
            label="Fecha",
            value=(
                partial.fecha.isoformat() if partial.fecha else date.today().isoformat()
            ),
            expand=True,
        )

        # Dropdown de categoría con sugerencia pre-seleccionada
        categoria_val = None
        if partial.categoria_sugerida:
            for cat in ExpenseCategory:
                if cat.value == partial.categoria_sugerida:
                    categoria_val = cat.value
                    break
        self._categoria_dropdown = ft.Dropdown(
            label="Categoría",
            value=categoria_val,
            expand=True,
            options=[ft.dropdown.Option(cat.value) for cat in ExpenseCategory],
        )

        self._metodo_dropdown = ft.Dropdown(
            label="Método de pago",
            value=PaymentMethod.EFECTIVO.value,
            expand=True,
            options=[ft.dropdown.Option(m.value) for m in PaymentMethod],
        )

        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(conf_icon, color=conf_color),
                        ft.Text(conf_label, color=conf_color, size=13),
                    ]
                ),
                ft.Divider(),
                ft.Text(
                    "Revisá y confirmá los datos del ticket",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Row(controls=[self._monto_field, self._fecha_field]),
                self._descripcion_field,
                ft.Row(controls=[self._categoria_dropdown, self._metodo_dropdown]),
                ft.Container(height=8),
                ft.Row(
                    controls=[
                        ft.Button(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.SAVE),
                                    ft.Text("Guardar gasto"),
                                ],
                                spacing=8,
                                tight=True,
                            ),
                            on_click=self._on_confirmar,
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.GREEN_600,
                                color=ft.Colors.WHITE,
                            ),
                        ),
                        ft.Button(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.DELETE),
                                    ft.Text("Descartar"),
                                ],
                                spacing=8,
                                tight=True,
                            ),
                            on_click=lambda _: self._cambiar_estado(_Estado.IDLE),
                            style=ft.ButtonStyle(
                                side=ft.BorderSide(1, ft.Colors.GREY_400),
                            ),
                        ),
                    ]
                ),
            ]
        )

    # ------------------------------------------------------------------
    # Estado ERROR
    # ------------------------------------------------------------------

    def _build_error(self) -> ft.Control:
        return ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(height=24),
                ft.Icon(ft.Icons.ERROR_OUTLINE, size=60, color=ft.Colors.RED_400),
                ft.Text(
                    "No se pudo procesar el ticket",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Text(
                    "Podés intentarlo de nuevo o cargar el gasto manualmente.",
                    size=13,
                    color=ft.Colors.GREY_600,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=16),
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        ft.Button(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.REFRESH),
                                    ft.Text("Intentar de nuevo"),
                                ],
                                spacing=8,
                                tight=True,
                            ),
                            on_click=lambda _: self._cambiar_estado(_Estado.IDLE),
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.ORANGE_500,
                                color=ft.Colors.WHITE,
                            ),
                        ),
                        ft.Button(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.EDIT),
                                    ft.Text("Cargar manualmente"),
                                ],
                                spacing=8,
                                tight=True,
                            ),
                            on_click=lambda _: self.router.navigate("/expenses"),
                            style=ft.ButtonStyle(
                                side=ft.BorderSide(1, ft.Colors.GREY_400),
                            ),
                        ),
                    ],
                ),
            ],
        )

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _cambiar_estado(self, nuevo: _Estado):
        self._estado = nuevo
        self._renderizar()

    async def _recuperar_pendiente(self) -> None:
        """Al inicializar, busca si hay un resultado OCR pendiente para esta familia.
        Si existe, salta directo a CONFIRM sin necesidad de re-subir la foto.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{_OCR_INTERNAL}/pendiente/{self._familia_id}")
                data = resp.json()
            if data.get("ready"):
                self._session_id = data.get("session_id")
                await self._procesar_resultado_ocr(data)
        except Exception as e:
            logger.debug("[OCR] Sin pendiente al iniciar: %s", e)

    def _preparar_sesion(self) -> str:
        """Genera un session_id y retorna la URL publica del formulario."""
        self._session_id = str(uuid.uuid4())
        return (
            f"{_OCR_PUBLIC}/upload-form"
            f"?session_id={self._session_id}"
            f"&familia_id={self._familia_id}"
        )

    async def _iniciar_polling(self, _):
        """Polling en background: espera el resultado OCR y avanza solo.
        Permanece en IDLE hasta recibir el resultado; solo entonces
        cambia a LOADING brevemente antes de pasar a CONFIRM o ERROR.
        """
        max_espera = 120  # segundos maximos esperando
        intervalo = 2  # segundos entre cada polling
        intentos = max_espera // intervalo

        for i in range(intentos):
            await asyncio.sleep(intervalo)

            if self._estado != _Estado.IDLE:
                return

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        f"{_OCR_INTERNAL}/resultado/{self._session_id}"
                    )
                    data = resp.json()
            except Exception as e:
                logger.warning("[OCR] Polling error intento %d: %s", i, e)
                continue

            if not data.get("ready"):
                continue

            self._cambiar_estado(_Estado.LOADING)
            await self._procesar_resultado_ocr(data)
            return

        logger.warning("[OCR] Timeout esperando foto session=%s", self._session_id)

    async def _procesar_resultado_ocr(self, data: dict) -> None:
        """Procesa el resultado OCR ya recibido y cambia al estado final."""
        await self._actualizar_loading(
            "Procesando con OCR...",
            "Tesseract + Gemma2 analizando el ticket",
        )

        if not data.get("success"):
            logger.error("[OCR] Error: %s", data.get("error"))
            self._cambiar_estado(_Estado.ERROR)
            return

        fecha_val = None
        if data.get("fecha"):
            try:
                fecha_val = date.fromisoformat(data["fecha"])
            except (ValueError, TypeError):
                pass

        self._partial = PartialExpense(
            monto=data.get("monto"),
            fecha=fecha_val,
            comercio=data.get("comercio"),
            items=data.get("items") or [],
            categoria_sugerida=data.get("categoria_sugerida"),
            confianza_ocr=data.get("confianza_ocr", 0.0),
            texto_crudo=data.get("texto_crudo", ""),
        )
        self._cambiar_estado(_Estado.CONFIRM)

    async def _actualizar_loading(self, titulo: str, subtitulo: str = ""):
        """Actualiza el texto del spinner sin reconstruir toda la vista."""
        self._loading_text.value = titulo
        self._loading_sub.value = subtitulo
        if hasattr(self.page, "update"):
            self.page.update()

    def _on_confirmar(self, _):
        """Guarda el gasto con los datos confirmados/editados por el usuario."""
        try:
            monto = float(self._monto_field.value or "0")
            if monto <= 0:
                self.page.overlay.append(
                    ft.SnackBar(ft.Text("El monto debe ser mayor a 0"), open=True)
                )
                self.page.update()
                return

            fecha_str = self._fecha_field.value or date.today().isoformat()
            try:
                fecha = date.fromisoformat(fecha_str)
            except ValueError:
                fecha = date.today()

            categoria_val = self._categoria_dropdown.value
            if not categoria_val:
                self.page.overlay.append(
                    ft.SnackBar(ft.Text("Seleccioná una categoría"), open=True)
                )
                self.page.update()
                return

            categoria = next(
                (c for c in ExpenseCategory if c.value == categoria_val),
                ExpenseCategory.OTROS,
            )
            metodo = next(
                (m for m in PaymentMethod if m.value == self._metodo_dropdown.value),
                PaymentMethod.EFECTIVO,
            )

            gasto = Expense(
                descripcion=self._descripcion_field.value or "Ticket OCR",
                monto=monto,
                categoria=categoria,
                metodo_pago=metodo,
                fecha=fecha,
                es_recurrente=False,
            )

            resultado = self.expense_controller.add_expense(gasto)
            if isinstance(resultado, Ok):
                self.page.overlay.append(
                    ft.SnackBar(ft.Text("✅ Gasto guardado correctamente"), open=True)
                )
                self.page.update()
                self.router.navigate("/expenses")
            else:
                self.page.overlay.append(
                    ft.SnackBar(ft.Text(f"Error: {resultado.err().message}"), open=True)
                )
                self.page.update()

        except Exception as ex:
            logger.error("[VISTA] Error al confirmar ticket: %s", ex)
            self.page.overlay.append(
                ft.SnackBar(ft.Text("Error al guardar el gasto"), open=True)
            )
            self.page.update()
