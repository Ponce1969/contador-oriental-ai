"""
Vista para carga y confirmación de tickets OCR.
Estados: IDLE → LOADING → CONFIRM → ERROR
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import date
from enum import Enum, auto

import flet as ft
from result import Ok

from controllers.expense_controller import ExpenseController
from controllers.ocr_controller import OCRController
from core.session import SessionManager
from models.categories import ExpenseCategory, PaymentMethod
from models.expense_model import Expense
from models.ticket_model import PartialExpense
from views.layouts.main_layout import MainLayout

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
        self.ocr_controller = OCRController(familia_id=familia_id)
        self.expense_controller = ExpenseController(familia_id=familia_id)

        self._estado = _Estado.IDLE
        self._partial: PartialExpense | None = None
        self._imagen_path: str | None = None

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

    def _build_idle(self) -> ft.Control:
        return ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.CAMERA_ALT, size=80, color=ft.Colors.BLUE_400),
                ft.Text(
                    "Cargar ticket de compra",
                    size=22,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Text(
                    "El sistema leerá el monto, fecha y comercio automáticamente.",
                    size=14,
                    color=ft.Colors.GREY_600,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=8),
                ft.Card(
                    content=ft.Container(
                        padding=16,
                        content=ft.Column(
                            controls=[
                                ft.ListTile(
                                    leading=ft.Icon(
                                        ft.Icons.LIGHTBULB,
                                        color=ft.Colors.AMBER,
                                    ),
                                    title=ft.Text("Consejos para mejor resultado"),
                                ),
                                ft.Text(
                                    "• Fotografiá el ticket sobre superficie plana",
                                    size=13,
                                ),
                                ft.Text("• Buena iluminación, evitá sombras", size=13),
                                ft.Text(
                                    "• Encuadrá todo el ticket en la foto",
                                    size=13,
                                ),
                                ft.Text("• El total debe ser visible", size=13),
                            ]
                        ),
                    )
                ),
                ft.Container(height=16),
                ft.ElevatedButton(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.UPLOAD_FILE),
                            ft.Text("Seleccionar foto del ticket"),
                        ],
                        spacing=8,
                        tight=True,
                    ),
                    on_click=lambda _: asyncio.create_task(
                        self._abrir_selector()
                    ),
                    style=ft.ButtonStyle(
                        padding=ft.padding.symmetric(horizontal=32, vertical=16)
                    ),
                ),
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
                ft.Container(
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.START,
                        controls=[
                            self._paso_item("1", "Preprocesando imagen"),
                            self._paso_item("2", "Tesseract extrae el texto"),
                            self._paso_item("3", "Gemma analiza montos y fechas"),
                            self._paso_item("4", "Buscando categoría por similitud"),
                        ],
                    ),
                    padding=ft.padding.symmetric(horizontal=32),
                ),
            ],
        )

    @staticmethod
    def _paso_item(num: str, texto: str) -> ft.Control:
        return ft.Row(
            controls=[
                ft.Container(
                    content=ft.Text(
                        num, size=11, color=ft.Colors.WHITE,
                        weight=ft.FontWeight.BOLD,
                    ),
                    width=22,
                    height=22,
                    border_radius=11,
                    bgcolor=ft.Colors.ORANGE_400,
                    alignment=ft.Alignment(0, 0),
                ),
                ft.Text(texto, size=13, color=ft.Colors.GREY_600),
            ],
            spacing=10,
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
                partial.fecha.isoformat() if partial.fecha
                else date.today().isoformat()
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
                        ft.ElevatedButton(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.SAVE),
                                    ft.Text("Guardar gasto"),
                                ],
                                spacing=8,
                                tight=True,
                            ),
                            on_click=self._on_confirmar,
                        ),
                        ft.OutlinedButton(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.DELETE),
                                    ft.Text("Descartar"),
                                ],
                                spacing=8,
                                tight=True,
                            ),
                            on_click=lambda _: self._cambiar_estado(_Estado.IDLE),
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
                        ft.ElevatedButton(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.REFRESH),
                                    ft.Text("Intentar de nuevo"),
                                ],
                                spacing=8,
                                tight=True,
                            ),
                            on_click=lambda _: self._cambiar_estado(_Estado.IDLE),
                        ),
                        ft.OutlinedButton(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.EDIT),
                                    ft.Text("Cargar manualmente"),
                                ],
                                spacing=8,
                                tight=True,
                            ),
                            on_click=lambda _: self.router.navigate("/expenses"),
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

    async def _abrir_selector(self):
        """Abre el selector de archivos usando el FilePicker del MainLayout."""
        picker = (
            self.page.data.get("_file_picker")
            if isinstance(self.page.data, dict)
            else None
        )
        if picker is None:
            logger.warning("[OCR] FilePicker no disponible aun, reintentando")
            return
        files = await picker.pick_files(
            allow_multiple=False,
            allowed_extensions=["jpg", "jpeg", "png", "webp"],
        )
        if not files:
            return
        self._imagen_path = files[0].path
        self._cambiar_estado(_Estado.LOADING)
        await self._procesar_imagen()

    async def _procesar_imagen(self):
        if not self._imagen_path:
            self._cambiar_estado(_Estado.ERROR)
            return

        await self._actualizar_loading(
            "Preprocesando imagen...",
            "Escala de grises → contraste → nitidez",
        )
        await asyncio.sleep(0.1)  # cede el event loop para que se pinte

        resultado = await self.ocr_controller.procesar_ticket(
            self._imagen_path,
            on_progreso=self._actualizar_loading,
        )

        if isinstance(resultado, Ok):
            self._partial = resultado.ok()
            self._cambiar_estado(_Estado.CONFIRM)
        else:
            logger.error("[VISTA] Error OCR: %s", resultado.err().message)
            self._cambiar_estado(_Estado.ERROR)

    async def _actualizar_loading(self, titulo: str, subtitulo: str = ""):
        """Actualiza el texto del spinner sin reconstruir toda la vista."""
        self._loading_text.value = titulo
        self._loading_sub.value = subtitulo
        if hasattr(self.page, "update"):
            self.page.update()

    def _limpiar_imagen_temporal(self):
        """Borra la imagen si APP_ENV=production (privacidad + espacio)."""
        if os.getenv("APP_ENV") != "production":
            return
        if self._imagen_path and os.path.exists(self._imagen_path):
            try:
                os.remove(self._imagen_path)
                logger.info("[OCR] Imagen temporal eliminada: %s", self._imagen_path)
            except OSError as e:
                logger.warning("[OCR] No se pudo borrar imagen: %s", e)

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
                self._limpiar_imagen_temporal()
                self.page.overlay.append(
                    ft.SnackBar(ft.Text("✅ Gasto guardado correctamente"), open=True)
                )
                self.page.update()
                self.router.navigate("/expenses")
            else:
                self.page.overlay.append(
                    ft.SnackBar(
                        ft.Text(f"Error: {resultado.err().message}"), open=True
                    )
                )
                self.page.update()

        except Exception as ex:
            logger.error("[VISTA] Error al confirmar ticket: %s", ex)
            self.page.overlay.append(
                ft.SnackBar(ft.Text("Error al guardar el gasto"), open=True)
            )
            self.page.update()
