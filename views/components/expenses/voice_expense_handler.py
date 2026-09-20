"""Modular Voice Expense Handler for Flet.

Coordinates voice recording, polling, entity normalization,
confirmation dialogs, and logging for the voice-to-expense pipeline.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

import flet as ft
import httpx

from models.categories import (
    ExpenseCategory,
    PaymentMethod,
    get_categories_for_entorno,
    get_subcategories,
)
from views.components.voice_expense_dialog import VoiceExpenseDialog

if TYPE_CHECKING:
    from flet import Page

logger = logging.getLogger("VoiceExpenseHandler")


@dataclass
class VoiceExpenseData:
    """Normalized domain data extracted from voice input."""

    monto: Decimal
    currency: str
    descripcion: str
    categoria: ExpenseCategory
    subcategoria: str | None
    metodo_pago: PaymentMethod
    fecha: date
    raw_text: str | None = None


# Module-level registry so sessions processed once are never re-processed
# across reconnects
_PROCESSED_SESSIONS: set[str] = set()


class VoiceExpenseHandler:
    """Encapsulates voice recording integration, polling, and data normalization."""

    def __init__(
        self,
        page: Page,
        familia_id: int,
        on_save_expense: Callable[[VoiceExpenseData], None],
        on_populate_form: Callable[[VoiceExpenseData], None] | None = None,
        entorno: str = "hogar",
    ) -> None:
        self.page = page
        self.familia_id = familia_id
        self.on_save_expense = on_save_expense
        self.on_populate_form = on_populate_form
        self.entorno = entorno
        self._processed_sessions = _PROCESSED_SESSIONS
        self._active_dialog: ft.AlertDialog | None = None
        self._recovery_task: asyncio.Task | None = None

    def open_voice_dialog(self, _: ft.ControlEvent | None = None) -> None:
        """Opens voice recording modal initiating the voice-to-expense flow."""
        try:
            logger.info(
                "[VOICE_HANDLER] Opening voice recording dialog for family_id=%d",
                self.familia_id,
            )
            VoiceExpenseDialog.show(
                self.page,
                self.handle_voice_result,
                familia_id=self.familia_id,
            )
        except Exception as e:
            logger.exception("[VOICE_HANDLER] Failed to open voice dialog: %s", e)
            self._show_snackbar(f"Error al abrir grabadora: {e}", is_error=True)

    def extract_session_id(self) -> str | None:
        """Extract voice_session parameter from page.query, page.route, or page.url."""
        # 1. page.query (QueryString)
        if hasattr(self.page, "query") and self.page.query:
            with contextlib.suppress(KeyError, TypeError, AttributeError):
                session_id = self.page.query.get("voice_session")
                if session_id:
                    logger.info(
                        "[VOICE_HANDLER] Session ID extracted from page.query: %s",
                        session_id,
                    )
                    return session_id

        # 2. page.route
        route = getattr(self.page, "route", "")
        if route and "?" in route:
            with contextlib.suppress(Exception):
                params = parse_qs(urlparse(route).query)
                if "voice_session" in params:
                    session_id = params["voice_session"][0]
                    logger.info(
                        "[VOICE_HANDLER] Session ID extracted from page.route: %s",
                        session_id,
                    )
                    return session_id

        # 3. page.url
        url = getattr(self.page, "url", "")
        if url and "?" in url:
            with contextlib.suppress(Exception):
                params = parse_qs(urlparse(url).query)
                if "voice_session" in params:
                    session_id = params["voice_session"][0]
                    logger.info(
                        "[VOICE_HANDLER] Session ID extracted from page.url: %s",
                        session_id,
                    )
                    return session_id

        return None

    def start_pending_recovery(self, session_id: str | None = None) -> None:
        """Schedules async background recovery of pending voice sessions."""
        target_session = session_id or self.extract_session_id()
        if self._recovery_task and not self._recovery_task.done():
            self._recovery_task.cancel()
            self._recovery_task = None

        if hasattr(self.page, "run_task"):
            self._recovery_task = self.page.run_task(
                self.recover_pending_voice_session, target_session
            )
        else:
            try:
                loop = asyncio.get_running_loop()
                self._recovery_task = loop.create_task(
                    self.recover_pending_voice_session(target_session)
                )
            except RuntimeError:
                logger.warning(
                    "[VOICE_HANDLER] No running loop to schedule voice recovery"
                )

    async def recover_pending_voice_session(
        self, session_id: str | None = None
    ) -> None:
        """Polls voice_api for completed audio processing jobs.

        Uses an extended timeout (60s) suitable for ARM64 inference (Orange Pi).
        """
        sid = session_id or self.extract_session_id()
        if sid and sid in self._processed_sessions:
            logger.info(
                "[VOICE_HANDLER] Session %s already processed; skipping recovery",
                sid,
            )
            return

        if not sid:
            logger.debug(
                "[VOICE_HANDLER] No voice_session query param; checking family fallback"
            )

        voice_url = os.getenv("VOICE_API_URL", "http://voice_api:8553")
        max_attempts = 40  # 40 * 1.5s = 60 seconds polling window
        interval = 1.5

        logger.info(
            "[VOICE_HANDLER] Starting polling (url=%s, sid=%s, fam_id=%d, wait=%.1fs)",
            voice_url,
            sid,
            self.familia_id,
            max_attempts * interval,
        )

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                for attempt in range(max_attempts):
                    if sid:
                        endpoint = f"{voice_url}/voice-resultado/{sid}"
                    else:
                        endpoint = f"{voice_url}/pendiente/{self.familia_id}"

                    try:
                        resp = await client.get(endpoint)
                        if resp.status_code == 200:
                            data = resp.json()
                            status = data.get("status")
                            ready = data.get("ready")
                            success = data.get("success")

                            logger.info(
                                "[VOICE_HANDLER] Poll %d/%d: ready=%s, status=%s",
                                attempt + 1,
                                max_attempts,
                                ready,
                                status,
                            )

                            if ready:
                                if sid and "session_id" not in data:
                                    data["session_id"] = sid
                                if success:
                                    logger.info(
                                        "[VOICE_HANDLER] Voice job ready: %s",
                                        data,
                                    )
                                    self.handle_voice_result(data)
                                else:
                                    err = data.get("error", "Error procesando audio")
                                    logger.warning(
                                        "[VOICE_HANDLER] Voice job error: %s",
                                        err,
                                    )
                                    self._clean_voice_url()
                                    self._show_snackbar(
                                        f"❌ Audio no procesado: {err}", is_error=True
                                    )
                                return
                    except Exception as req_err:
                        logger.debug(
                            "[VOICE_HANDLER] Polling error on attempt %d: %s",
                            attempt + 1,
                            req_err,
                        )

                    await asyncio.sleep(interval)

            logger.info(
                "[VOICE_HANDLER] Polling loop completed without ready job (timeout)"
            )
            self._clean_voice_url()
        except asyncio.CancelledError:
            logger.info("[VOICE_HANDLER] Polling task cancelled")
        except Exception as e:
            logger.exception(
                "[VOICE_HANDLER] Unexpected exception during voice recovery: %s", e
            )

    def normalize_voice_data(self, data: dict) -> VoiceExpenseData:
        """Normalizes and validates raw voice payload into VoiceExpenseData.

        Guarantees that mandatory fields (monto, descripcion, categoria)
        have valid values.
        """
        # 1. Monto
        raw_monto = data.get("monto")
        monto = Decimal("0")
        if raw_monto is not None:
            try:
                monto = (
                    raw_monto
                    if isinstance(raw_monto, Decimal)
                    else Decimal(str(raw_monto))
                )
            except (InvalidOperation, ValueError, TypeError) as conv_err:
                logger.warning(
                    "[VOICE_HANDLER] Could not parse amount '%s': %s",
                    raw_monto,
                    conv_err,
                )
                monto = Decimal("0")

        # 2. Descripción: Guaranteed to never be empty
        comercio = data.get("comercio")
        notas = data.get("notas")
        raw_text = data.get("text")
        descripcion = (
            comercio or notas or raw_text or "Gasto registrado por voz"
        ).strip()
        if not descripcion:
            descripcion = "Gasto registrado por voz"

        # 3. Currency
        currency = data.get("currency")
        if currency not in ("UYU", "USD"):
            currency = "USD" if self.entorno == "campo" else "UYU"

        # 4. Categoría
        available_categories = get_categories_for_entorno(self.entorno)
        raw_cat = (data.get("categoria") or "").strip()
        matched_category = self._match_category(raw_cat, available_categories)

        # Fallback category based on description if unmapped
        if not matched_category:
            matched_category = self._infer_category_from_text(
                descripcion, available_categories
            )

        # 5. Subcategoría
        subcategoria = data.get("subcategoria")
        valid_subcategories = get_subcategories(matched_category.value)
        if subcategoria and subcategoria not in valid_subcategories:
            subcategoria = None

        # 6. Método de pago
        raw_mp = (data.get("medio_pago") or "").strip()
        matched_mp = self._match_payment_method(raw_mp)

        return VoiceExpenseData(
            monto=monto,
            currency=currency,
            descripcion=descripcion,
            categoria=matched_category,
            subcategoria=subcategoria,
            metodo_pago=matched_mp,
            fecha=date.today(),
            raw_text=raw_text,
        )

    def handle_voice_result(self, data: dict) -> None:
        """Processes received voice payload and displays confirmation modal."""
        session_id = data.get("session_id") or self.extract_session_id()
        if session_id and session_id in self._processed_sessions:
            logger.info(
                "[VOICE_HANDLER] Session %s already processed; skipping duplicate",
                session_id,
            )
            return

        if self._active_dialog and getattr(self._active_dialog, "open", False):
            logger.info(
                "[VOICE_HANDLER] Confirmation dialog already active; skipping duplicate"
            )
            return

        if session_id:
            self._processed_sessions.add(session_id)

        logger.info(
            "[VOICE_HANDLER] Handling voice result payload: %s",
            {k: v for k, v in data.items() if k != "audio"},
        )
        try:
            norm = self.normalize_voice_data(data)
            logger.info(
                "[VOICE_HANDLER] Parsed: Desc='%s', Monto=%s %s, Cat='%s'",
                norm.descripcion,
                norm.monto,
                norm.currency,
                norm.categoria.value,
            )
            self._show_confirmation_dialog(norm)
        except Exception as e:
            logger.exception(
                "[VOICE_HANDLER] Failed to handle and display voice result: %s", e
            )
            self._show_snackbar(
                f"Error al procesar el audio dictado: {e}", is_error=True
            )

    def _show_confirmation_dialog(self, expense_data: VoiceExpenseData) -> None:
        """Renders interactive confirmation modal with editable fields (like OCR)."""
        monto_str = (
            f"{expense_data.monto:f}".rstrip("0").rstrip(".")
            if "." in str(expense_data.monto)
            else str(expense_data.monto)
        )

        available_categories = get_categories_for_entorno(self.entorno)

        # Controles editables pre-poblados
        descripcion_tf = ft.TextField(
            label="Concepto / Comercio",
            value=expense_data.descripcion,
            dense=True,
            expand=True,
        )

        monto_tf = ft.TextField(
            label="Monto",
            value=monto_str,
            keyboard_type=ft.KeyboardType.NUMBER,
            dense=True,
            expand=True,
        )

        currency_dd = ft.Dropdown(
            label="Moneda",
            value=expense_data.currency,
            options=[
                ft.dropdown.Option("UYU"),
                ft.dropdown.Option("USD"),
            ],
            dense=True,
            width=100,
        )

        categoria_dd = ft.Dropdown(
            label="Categoría",
            value=expense_data.categoria.value,
            options=[ft.dropdown.Option(cat.value) for cat in available_categories],
            dense=True,
            expand=True,
        )

        metodo_dd = ft.Dropdown(
            label="Medio de pago",
            value=expense_data.metodo_pago.value,
            options=[ft.dropdown.Option(mp.value) for mp in PaymentMethod],
            dense=True,
            expand=True,
        )

        is_saving = False

        def _get_edited_data() -> VoiceExpenseData:
            try:
                raw_m = monto_tf.value.strip() if monto_tf.value else "0"
                final_monto = Decimal(raw_m)
            except Exception:
                final_monto = expense_data.monto

            raw_desc = (descripcion_tf.value or "").strip()
            final_desc = raw_desc or expense_data.descripcion
            final_currency = currency_dd.value or expense_data.currency
            final_cat = (
                self._match_category(categoria_dd.value or "", available_categories)
                or expense_data.categoria
            )
            final_mp = self._match_payment_method(metodo_dd.value or "")

            return VoiceExpenseData(
                monto=final_monto,
                currency=final_currency,
                descripcion=final_desc,
                categoria=final_cat,
                subcategoria=expense_data.subcategoria,
                metodo_pago=final_mp,
                fecha=expense_data.fecha,
                raw_text=expense_data.raw_text,
            )

        def _on_dismiss(_: ft.ControlEvent | None = None) -> None:
            confirm_dialog.open = False
            self._active_dialog = None
            self._clean_voice_url()

        def _close_dialog() -> None:
            confirm_dialog.open = False
            self._active_dialog = None
            self._clean_voice_url()
            if hasattr(self.page, "update"):
                self.page.update()

        def _confirm_and_save(_: ft.ControlEvent | None = None) -> None:
            nonlocal is_saving
            if is_saving:
                logger.warning(
                    "[VOICE_HANDLER] Save already in progress, ignoring duplicate click"
                )
                return
            is_saving = True

            final_data = _get_edited_data()
            _close_dialog()

            logger.info(
                "[VOICE_HANDLER] User confirmed voice expense saving: %s ($%s %s)",
                final_data.descripcion,
                final_data.monto,
                final_data.currency,
            )
            try:
                self.on_save_expense(final_data)
            except Exception as save_err:
                logger.exception(
                    "[VOICE_HANDLER] Error in on_save_expense callback: %s", save_err
                )
                self._show_snackbar(
                    f"Error al guardar gasto: {save_err}", is_error=True
                )

        def _dismiss_and_edit(_: ft.ControlEvent | None = None) -> None:
            final_data = _get_edited_data()
            _close_dialog()

            logger.info(
                "[VOICE_HANDLER] User chose to edit in page form: %s",
                final_data.descripcion,
            )
            if self.on_populate_form:
                self.on_populate_form(final_data)

        def _cancel(_: ft.ControlEvent | None = None) -> None:
            _close_dialog()
            logger.info("[VOICE_HANDLER] User dismissed voice confirmation dialog")

        confirm_dialog = ft.AlertDialog(
            modal=True,
            on_dismiss=_on_dismiss,
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.AUTO_AWESOME, color=ft.Colors.GREEN_600, size=24),
                    ft.Text(
                        "Confirmar Gasto por Voz",
                        weight=ft.FontWeight.BOLD,
                        size=18,
                    ),
                ],
                spacing=8,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "Revisá o modificá los datos interpretados antes de "
                            "guardar:",
                            size=12,
                            color=ft.Colors.GREY_700,
                        ),
                        ft.Container(height=4),
                        descripcion_tf,
                        ft.Row(
                            controls=[monto_tf, currency_dd],
                            spacing=8,
                        ),
                        categoria_dd,
                        metodo_dd,
                    ],
                    tight=True,
                    spacing=10,
                ),
                width=420,
            ),
            actions=[
                ft.TextButton("Cargar en formulario", on_click=_dismiss_and_edit),
                ft.TextButton("Cancelar", on_click=_cancel),
                ft.ElevatedButton(
                    "💾 Confirmar y Guardar",
                    bgcolor=ft.Colors.GREEN_700,
                    color=ft.Colors.WHITE,
                    on_click=_confirm_and_save,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # Ensure any old dialog is marked closed
        if self._active_dialog:
            self._active_dialog.open = False

        self._active_dialog = confirm_dialog
        if confirm_dialog not in self.page.overlay:
            self.page.overlay.append(confirm_dialog)
        confirm_dialog.open = True
        self.page.update()

    def _clean_voice_url(self) -> None:
        """Removes voice_session from page.query and page.route."""
        if hasattr(self.page, "query") and isinstance(self.page.query, dict):
            self.page.query.pop("voice_session", None)
        route = getattr(self.page, "route", "")
        if route and "voice_session" in route:
            self.page.route = route.split("?")[0]

    @staticmethod
    def _clean_string(text: str) -> str:
        """Removes emojis, punctuation, and extraneous spaces for robust matching."""
        return re.sub(r"[^\w\s]", "", text.lower()).strip()

    def _match_category(
        self, raw_cat: str, available_categories: list[ExpenseCategory]
    ) -> ExpenseCategory | None:
        """Fuzzy matches raw category string against available enum values."""
        if not raw_cat:
            return None

        clean_raw = self._clean_string(raw_cat)
        for cat in available_categories:
            clean_cat = self._clean_string(cat.value)
            if (
                clean_raw == clean_cat
                or clean_raw in clean_cat
                or clean_cat in clean_raw
            ):
                return cat
        return None

    def _infer_category_from_text(
        self, text: str, available_categories: list[ExpenseCategory]
    ) -> ExpenseCategory:
        """Heuristically infers category from text keywords or falls back to OTROS."""
        text_lower = text.lower()
        if any(
            k in text_lower
            for k in (
                "cafe",
                "café",
                "restaurante",
                "bar",
                "comida",
                "salida",
                "almuerzo",
                "cena",
            )
        ):
            if ExpenseCategory.OCIO in available_categories:
                return ExpenseCategory.OCIO

        if any(
            k in text_lower
            for k in ("super", "almacen", "almacén", "leche", "pan", "disco", "devoto")
        ):
            if ExpenseCategory.ALMACEN in available_categories:
                return ExpenseCategory.ALMACEN

        if any(
            k in text_lower
            for k in ("nafta", "gasoil", "combustible", "ancap", "auto", "taller")
        ):
            if ExpenseCategory.VEHICULOS in available_categories:
                return ExpenseCategory.VEHICULOS

        if any(
            k in text_lower
            for k in ("farmacia", "farmashop", "medicamento", "remedio", "medico")
        ):
            if ExpenseCategory.SALUD in available_categories:
                return ExpenseCategory.SALUD

        if ExpenseCategory.OTROS in available_categories:
            return ExpenseCategory.OTROS

        return available_categories[0]

    def _match_payment_method(self, raw_mp: str) -> PaymentMethod:
        """Matches payment method string to PaymentMethod enum."""
        raw_lower = raw_mp.lower()
        if any(
            k in raw_lower
            for k in ("debito", "débito", "pos", "visa debito", "master debito")
        ):
            return PaymentMethod.TARJETA_DEBITO
        if any(k in raw_lower for k in ("credito", "crédito", "cuota", "oca")):
            return PaymentMethod.TARJETA_CREDITO
        if any(k in raw_lower for k in ("transferencia", "brou", "itau", "santander")):
            return PaymentMethod.TRANSFERENCIA
        return PaymentMethod.EFECTIVO

    def _show_snackbar(self, message: str, is_error: bool = False) -> None:
        """Helper to display feedback snackbars."""
        bg = ft.Colors.RED_700 if is_error else ft.Colors.GREEN_700
        snack = ft.SnackBar(content=ft.Text(message), open=True, bgcolor=bg)
        self.page.overlay.append(snack)
        self.page.update()
