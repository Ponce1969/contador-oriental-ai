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
from decimal import Decimal
from enum import Enum, auto

import flet as ft
import httpx
from result import Ok

from controllers.expense_controller import ExpenseController
from core.session import SessionManager
from core.sqlalchemy_session import get_db_session
from models.categories import ExpenseCategory, PaymentMethod
from models.expense_model import Expense
from models.ticket_model import PartialExpense
from services.infrastructure.quota_manager import QuotaManager
from views.layouts.main_layout import MainLayout

# URL interna Docker (Python->microservicio) y publica (browser->microservicio)
_OCR_INTERNAL = os.getenv("OCR_API_URL", "http://ocr_api:8551")
_OCR_PUBLIC = os.getenv("OCR_API_PUBLIC_URL", "/ocr")

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
        if familia_id is None:
            router.navigate("/login")
            return

        self._familia_id: int = int(familia_id)
        self.expense_controller = ExpenseController(familia_id=self._familia_id)

        self._estado = _Estado.IDLE
        self._partial: PartialExpense | None = None
        self._session_id: str | None = None
        self._engine: str = "cloud"
        self._quota_remaining: int = 10
        self._quota_limit: int = 10
        self._last_engine_used: str = "local"
        self._consultar_cuota_ocr()

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

    def _consultar_cuota_ocr(self) -> None:
        """Query OCR quota for the current family and set local engine as default."""
        try:
            with get_db_session() as session:
                qm = QuotaManager(session, self._familia_id)
                self._quota_limit = qm.ocr_daily_limit()
                self._quota_remaining = qm.get_remaining_ocr()
        except Exception as e:
            logger.warning("[OCR_VIEW] Could not query quota: %s", e)
            self._quota_remaining = 0
            self._quota_limit = 10

        # Consensus: Fast, private local pipeline on Orange Pi is the default
        self._engine = "local"

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

        cloud_available = self._quota_remaining > 0
        cloud_label = (
            f"⚡ Escaneo Rápido ({self._quota_remaining}/{self._quota_limit} hoy)"
        )
        local_label = "🔒 Escaneo 100% Local"

        def _on_engine_change(e):
            if e.control.value:
                self._engine = e.control.value
                self._renderizar()

        if cloud_available:
            info_text = (
                "⚡ Modo Rápido: Procesa el ticket en ~1-2s con Gemini 2.0 Flash."
                if self._engine == "cloud"
                else "🔒 Modo Local: Inferencia 100% privada con Orange Pi."
            )
            info_color = ft.Colors.GREY_600
        else:
            info_text = "⚠️ Cuota diaria de escaneo rápido agotada. Usando motor local."
            info_color = ft.Colors.ORANGE_800

        engine_selector = ft.Container(
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
                controls=[
                    ft.Text(
                        "Modo de escaneo:",
                        size=13,
                        weight=ft.FontWeight.W_500,
                        color=ft.Colors.GREY_700,
                    ),
                    ft.RadioGroup(
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.CENTER,
                            wrap=True,
                            spacing=16,
                            controls=[
                                ft.Radio(
                                    value="cloud",
                                    label=cloud_label,
                                    disabled=not cloud_available,
                                ),
                                ft.Radio(
                                    value="local",
                                    label=local_label,
                                ),
                            ],
                        ),
                        value=self._engine,
                        on_change=_on_engine_change,
                    ),
                    ft.Text(
                        info_text,
                        size=11,
                        color=info_color,
                        italic=True,
                    ),
                ],
            ),
            margin=ft.Margin.only(bottom=16),
        )

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
                ft.Container(height=16),
                engine_selector,
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

        # Chip de confianza OCR (3 tiers consensuados)
        if partial.monto is None or partial.confianza_ocr < 0.50:
            conf_color = ft.Colors.RED_700
            conf_label = (
                f"Baja confianza ({partial.confianza_ocr:.0%}) — completá datos"
                if partial.monto is not None
                else "Monto no detectado — por favor completalo"
            )
            conf_icon = ft.Icons.ERROR_OUTLINE
        elif partial.confianza_ocr >= 0.80:
            conf_color = ft.Colors.GREEN_700
            conf_label = f"Alta confianza ({partial.confianza_ocr:.0%})"
            conf_icon = ft.Icons.CHECK_CIRCLE
        else:
            conf_color = ft.Colors.ORANGE_700
            conf_label = (
                f"Confianza media ({partial.confianza_ocr:.0%}) — verificá datos"
            )
            conf_icon = ft.Icons.WARNING

        # Banner informativo de discrepancia aritmética (no altera montos visuales)
        discrepancy_banner = None
        if partial.arithmetic_consistent is False:
            discrepancy_banner = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.INFO_OUTLINE, color=ft.Colors.AMBER_900, size=16
                        ),
                        ft.Text(
                            "Diferencia en ticket impreso (Subtotal + IVA ≠ Total)",
                            size=12,
                            color=ft.Colors.AMBER_900,
                            weight=ft.FontWeight.W_500,
                        ),
                    ],
                    spacing=6,
                ),
                bgcolor=ft.Colors.AMBER_50,
                border=ft.Border.all(1, ft.Colors.AMBER_300),
                padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                border_radius=8,
                margin=ft.Margin.only(bottom=8),
            )

        # Banner de consentimiento opt-in no coercitivo para Gemini Flash
        fallback_banner = None
        if (
            (partial.confianza_ocr < 0.75 or partial.monto is None)
            and self._last_engine_used != "gemini-2.0-flash"
            and self._quota_remaining > 0
        ):
            fallback_banner = ft.Container(
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(
                                    ft.Icons.AUTO_AWESOME,
                                    color=ft.Colors.BLUE_700,
                                    size=18,
                                ),
                                ft.Text(
                                    "¿Querés mejorar los datos con Gemini Flash?",
                                    weight=ft.FontWeight.BOLD,
                                    size=13,
                                    color=ft.Colors.BLUE_900,
                                ),
                            ],
                            spacing=6,
                        ),
                        ft.Text(
                            "El escaneo local extrajo datos preliminares. "
                            "Podés procesar con Google Gemini en 1-2s para "
                            "máxima precisión o completar a mano.",
                            size=12,
                            color=ft.Colors.BLUE_800,
                        ),
                        ft.Button(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.BOLT, size=16),
                                    ft.Text(
                                        f"⚡ Procesar con Gemini Flash "
                                        f"({self._quota_remaining}/"
                                        f"{self._quota_limit} hoy)"
                                    ),
                                ],
                                spacing=6,
                                tight=True,
                            ),
                            on_click=self._on_reintentar_gemini,
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.BLUE_600,
                                color=ft.Colors.WHITE,
                            ),
                        ),
                    ],
                ),
                bgcolor=ft.Colors.BLUE_50,
                border=ft.Border.all(1, ft.Colors.BLUE_200),
                padding=ft.Padding.all(12),
                border_radius=8,
                margin=ft.Margin.only(bottom=12),
            )

        # Campos pre-llenados editables
        self._monto_field = ft.TextField(
            label="Monto ($)",
            value=str(partial.monto) if partial.monto else "",
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True,
            error_text="Ingresá el monto" if partial.monto is None else None,
            autofocus=partial.monto is None,
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

        # Chip del motor utilizado
        if self._last_engine_used == "gemini-2.0-flash":
            engine_chip = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.BOLT, color=ft.Colors.AMBER_800, size=15),
                        ft.Text(
                            "⚡ Procesado con Gemini Flash en 1s",
                            size=12,
                            color=ft.Colors.AMBER_900,
                            weight=ft.FontWeight.W_500,
                        ),
                    ],
                    spacing=4,
                    tight=True,
                ),
                bgcolor=ft.Colors.AMBER_50,
                border=ft.Border.all(1, ft.Colors.AMBER_200),
                padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                border_radius=8,
            )
        else:
            engine_chip = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.LOCK, color=ft.Colors.BLUE_800, size=15),
                        ft.Text(
                            "🔒 Procesado localmente con Orange Pi",
                            size=12,
                            color=ft.Colors.BLUE_900,
                            weight=ft.FontWeight.W_500,
                        ),
                    ],
                    spacing=4,
                    tight=True,
                ),
                bgcolor=ft.Colors.BLUE_50,
                border=ft.Border.all(1, ft.Colors.BLUE_200),
                padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                border_radius=8,
            )

        confirm_controls: list[ft.Control] = [
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(conf_icon, color=conf_color),
                            ft.Text(conf_label, color=conf_color, size=13),
                        ],
                        spacing=6,
                        tight=True,
                    ),
                    engine_chip,
                ],
            ),
            ft.Divider(),
        ]

        if fallback_banner is not None:
            confirm_controls.append(fallback_banner)

        if discrepancy_banner is not None:
            confirm_controls.append(discrepancy_banner)

        confirm_controls.extend(
            [
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

        return ft.Column(controls=confirm_controls)

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

    def _on_reintentar_gemini(self, _):
        """Dispara el reprocesamiento con Gemini Flash en la nube."""
        asyncio.create_task(self._ejecutar_reintento_gemini())

    async def _ejecutar_reintento_gemini(self):
        if not self._session_id:
            return
        self._cambiar_estado(_Estado.LOADING)
        await self._actualizar_loading(
            "Consultando Gemini Flash ⚡",
            "Extrayendo datos de alta precisión en la nube...",
        )
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{_OCR_INTERNAL}/retry-cloud/{self._session_id}"
                )
                data = resp.json()
                if not data.get("success"):
                    logger.warning("[OCR] Reintento fallido: %s", data.get("error"))
                    self._cambiar_estado(_Estado.CONFIRM)
                    return
            asyncio.create_task(self._iniciar_polling(None))
        except Exception as e:
            logger.error("[OCR] Error en reintento Gemini: %s", e, exc_info=True)
            self._cambiar_estado(_Estado.CONFIRM)

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
            f"&engine={self._engine}"
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

            if self._estado not in (_Estado.IDLE, _Estado.LOADING):
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
                if data.get("status") == "processing" and self._estado == _Estado.IDLE:
                    self._cambiar_estado(_Estado.LOADING)
                    await self._actualizar_loading(
                        "Foto recibida 📸",
                        "Analizando ticket en la Orange Pi...",
                    )
                continue

            try:
                if self._estado != _Estado.LOADING:
                    self._cambiar_estado(_Estado.LOADING)
                await self._procesar_resultado_ocr(data)
            except Exception as e:
                logger.error("[OCR] Error processing OCR result: %s", e, exc_info=True)
                self._cambiar_estado(_Estado.ERROR)
            return

        logger.warning("[OCR] Timeout esperando foto session=%s", self._session_id)
        if self._estado in (_Estado.IDLE, _Estado.LOADING):
            self._cambiar_estado(_Estado.ERROR)

    async def _procesar_resultado_ocr(self, data: dict) -> None:
        """Procesa el resultado OCR ya recibido y cambia al estado final."""
        engine_used = data.get("engine_used", "local")
        self._last_engine_used = engine_used

        if engine_used == "gemini-2.0-flash":
            try:
                with get_db_session() as session:
                    qm = QuotaManager(session, self._familia_id)
                    qm.register_cloud_ocr_usage()
                    self._quota_remaining = qm.get_remaining_ocr()
            except Exception as e:
                logger.warning("[OCR_VIEW] Failed to register cloud OCR usage: %s", e)

            await self._actualizar_loading(
                "Procesado con Gemini Flash ⚡",
                "Datos extraídos a través de la nube",
            )
        else:
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

        monto_val = data.get("monto")
        subtotal_val = data.get("subtotal")
        tax_val = data.get("tax")
        conf_val = float(
            data.get("extraction_confidence") or data.get("confianza_ocr") or 0.0
        )

        self._partial = PartialExpense(
            monto=Decimal(str(monto_val)) if monto_val is not None else None,
            subtotal=Decimal(str(subtotal_val)) if subtotal_val is not None else None,
            tax=Decimal(str(tax_val)) if tax_val is not None else None,
            rut=data.get("rut"),
            document_type=data.get("document_type"),
            fecha=fecha_val,
            comercio=data.get("comercio"),
            currency=data.get("currency") or "UYU",
            items=data.get("items") or [],
            categoria_sugerida=data.get("categoria_sugerida"),
            subcategoria_sugerida=data.get("subcategoria_sugerida"),
            confianza_ocr=conf_val,
            extraction_confidence=conf_val,
            arithmetic_consistent=data.get("arithmetic_consistent"),
            texto_crudo=data.get("texto_crudo", ""),
            engine_used=engine_used,
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
            monto = Decimal(self._monto_field.value or "0")
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
