"""Unit tests for VoiceExpenseHandler component."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.categories import ExpenseCategory, PaymentMethod
from views.components.expenses.voice_expense_handler import (
    VoiceExpenseData,
    VoiceExpenseHandler,
)


class TestVoiceDataNormalization:
    """Tests normalization of raw voice dicts into VoiceExpenseData."""

    @pytest.fixture
    def handler(self) -> VoiceExpenseHandler:
        page = MagicMock()
        return VoiceExpenseHandler(
            page=page,
            familia_id=1,
            on_save_expense=MagicMock(),
            on_populate_form=MagicMock(),
            entorno="hogar",
        )

    def test_normalizes_standard_supermarket_payload(
        self, handler: VoiceExpenseHandler
    ) -> None:
        raw_data = {
            "monto": 1450.50,
            "currency": "UYU",
            "comercio": "Devoto",
            "categoria": "🛒 Almacén",
            "subcategoria": "Supermercado",
            "medio_pago": "Tarjeta débito",
            "text": "mil cuatrocientos cincuenta en Devoto con debito",
        }

        result = handler.normalize_voice_data(raw_data)

        assert isinstance(result, VoiceExpenseData)
        assert result.monto == Decimal("1450.50")
        assert result.currency == "UYU"
        assert result.descripcion == "Devoto"
        assert result.categoria == ExpenseCategory.ALMACEN
        assert result.metodo_pago == PaymentMethod.TARJETA_DEBITO

    def test_fallback_description_when_comercio_and_notas_missing(
        self, handler: VoiceExpenseHandler
    ) -> None:
        raw_data = {
            "monto": Decimal("500"),
            "currency": "UYU",
            "comercio": None,
            "notas": None,
            "text": "gasté quinientos pesos",
        }

        result = handler.normalize_voice_data(raw_data)

        assert result.descripcion == "gasté quinientos pesos"

    def test_absolute_fallback_description_when_text_empty(
        self, handler: VoiceExpenseHandler
    ) -> None:
        raw_data = {
            "monto": Decimal("300"),
            "comercio": "",
            "notas": "",
            "text": "",
        }

        result = handler.normalize_voice_data(raw_data)

        assert result.descripcion == "Gasto registrado por voz"

    def test_fuzzy_category_matching_without_emojis_and_accents(
        self, handler: VoiceExpenseHandler
    ) -> None:
        # Regex or LLM might return 'almacen' without emoji or accent
        raw_data = {
            "monto": 250,
            "comercio": "Panadería",
            "categoria": "almacen",
        }

        result = handler.normalize_voice_data(raw_data)

        assert result.categoria == ExpenseCategory.ALMACEN

    def test_infers_category_from_keywords_when_unspecified(
        self, handler: VoiceExpenseHandler
    ) -> None:
        raw_data = {
            "monto": 180,
            "comercio": "Café Martínez",
            "categoria": None,
        }

        result = handler.normalize_voice_data(raw_data)

        assert result.categoria == ExpenseCategory.OCIO

    def test_infers_fuel_category_for_ancap(
        self, handler: VoiceExpenseHandler
    ) -> None:
        raw_data = {
            "monto": 2000,
            "comercio": "Ancap",
            "categoria": "",
            "medio_pago": "oca",
        }

        result = handler.normalize_voice_data(raw_data)

        assert result.categoria == ExpenseCategory.VEHICULOS
        assert result.metodo_pago == PaymentMethod.TARJETA_CREDITO

    def test_handles_invalid_or_missing_amount_gracefully(
        self, handler: VoiceExpenseHandler
    ) -> None:
        raw_data = {
            "monto": "invalido",
            "comercio": "Kiosko",
        }

        result = handler.normalize_voice_data(raw_data)

        assert result.monto == Decimal("0")


class TestSessionIdExtraction:
    """Tests extracting session_id from query params, route, or url."""

    def test_extract_from_page_query(self) -> None:
        page = MagicMock()
        page.query = {"voice_session": "test-session-123"}
        handler = VoiceExpenseHandler(page, 1, MagicMock())

        assert handler.extract_session_id() == "test-session-123"

    def test_extract_from_page_route(self) -> None:
        page = MagicMock()
        page.query = {}
        page.route = "/expenses?voice_session=route-session-456"
        handler = VoiceExpenseHandler(page, 1, MagicMock())

        assert handler.extract_session_id() == "route-session-456"

    def test_extract_from_page_url(self) -> None:
        page = MagicMock()
        page.query = None
        page.route = "/expenses"
        page.url = "http://192.168.1.50:8550/expenses?voice_session=url-session-789"
        handler = VoiceExpenseHandler(page, 1, MagicMock())

        assert handler.extract_session_id() == "url-session-789"

    def test_returns_none_when_no_session_present(self) -> None:
        page = MagicMock()
        page.query = None
        page.route = "/expenses"
        page.url = "http://localhost:8550/expenses"
        handler = VoiceExpenseHandler(page, 1, MagicMock())

        assert handler.extract_session_id() is None


class TestPendingVoiceRecoveryPolling:
    """Tests polling loop behavior against voice_api."""

    @pytest.mark.asyncio
    async def test_successful_polling_after_retries(self) -> None:
        page = MagicMock()
        page.query = {"voice_session": "async-sess-001"}
        save_cb = MagicMock()
        handler = VoiceExpenseHandler(page, 1, on_save_expense=save_cb)

        # Mock 1st call: status=processing, ready=False
        # Mock 2nd call: status=completed, ready=True, success=True
        mock_resp_1 = MagicMock()
        mock_resp_1.status_code = 200
        mock_resp_1.json.return_value = {
            "ready": False,
            "status": "processing",
        }

        mock_resp_2 = MagicMock()
        mock_resp_2.status_code = 200
        mock_resp_2.json.return_value = {
            "ready": True,
            "success": True,
            "monto": 900,
            "currency": "UYU",
            "comercio": "Farmashop",
            "categoria": "Salud",
            "medio_pago": "Efectivo",
        }

        client_mock = AsyncMock()
        client_mock.get.side_effect = [mock_resp_1, mock_resp_2]

        with patch("httpx.AsyncClient") as client_cls:
            client_cls.return_value.__aenter__.return_value = client_mock
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with patch.object(handler, "handle_voice_result") as mock_handle:
                    await handler.recover_pending_voice_session()
                    mock_handle.assert_called_once()
                    called_data = mock_handle.call_args[0][0]
                    assert called_data["comercio"] == "Farmashop"
                    assert called_data["monto"] == 900


class TestVoiceDeduplicationAndDialogSafety:
    """Tests that duplicate voice jobs and concurrent dialogs are rejected."""

    def test_deduplicates_same_session_id(self) -> None:
        page = MagicMock()
        page.overlay = []
        handler = VoiceExpenseHandler(page, 1, MagicMock())

        payload = {
            "session_id": "sess-unique-999",
            "monto": 250,
            "comercio": "Café",
            "categoria": "Ocio",
        }

        with patch.object(handler, "_show_confirmation_dialog") as mock_show:
            handler.handle_voice_result(payload)
            assert mock_show.call_count == 1

            # Calling again with same session_id should be skipped
            handler.handle_voice_result(payload)
            assert mock_show.call_count == 1

    def test_ignores_result_when_dialog_is_already_open(self) -> None:
        page = MagicMock()
        page.overlay = []
        handler = VoiceExpenseHandler(page, 1, MagicMock())

        # Simulate an already open dialog
        mock_dialog = MagicMock()
        mock_dialog.open = True
        handler._active_dialog = mock_dialog

        payload = {
            "session_id": "sess-another-111",
            "monto": 500,
            "comercio": "Devoto",
        }

        with patch.object(handler, "_show_confirmation_dialog") as mock_show:
            handler.handle_voice_result(payload)
            mock_show.assert_not_called()

    def test_prevents_multiple_saves_on_rapid_clicks(self) -> None:
        page = MagicMock()
        page.overlay = []
        save_mock = MagicMock()
        handler = VoiceExpenseHandler(page, 1, on_save_expense=save_mock)

        norm_data = handler.normalize_voice_data({
            "monto": 250,
            "comercio": "Café",
            "categoria": "Ocio",
        })

        handler._show_confirmation_dialog(norm_data)
        assert handler._active_dialog is not None

        # Extract the save button click handler (last action button)
        confirm_btn = handler._active_dialog.actions[-1]
        on_click = confirm_btn.on_click

        # First click triggers save
        on_click(MagicMock())
        assert save_mock.call_count == 1

        # Second rapid click should be ignored by the is_saving guard
        on_click(MagicMock())
        assert save_mock.call_count == 1

    def test_saves_edited_values_from_modal(self) -> None:
        page = MagicMock()
        page.overlay = []
        save_mock = MagicMock()
        handler = VoiceExpenseHandler(page, 1, on_save_expense=save_mock)

        norm_data = handler.normalize_voice_data({
            "monto": 250,
            "comercio": "Farmashore",
            "categoria": "Almacén",
        })

        handler._show_confirmation_dialog(norm_data)
        dialog = handler._active_dialog
        assert dialog is not None

        # Modify values directly in modal controls
        col_controls = dialog.content.content.controls
        # [0]=Text, [1]=Container, [2]=descripcion_tf, [3]=Row(monto, currency), [4]=categoria, [5]=metodo
        desc_tf = col_controls[2]
        desc_tf.value = "Farmashop"

        monto_tf = col_controls[3].controls[0]
        monto_tf.value = "320"

        # Click confirm
        confirm_btn = dialog.actions[-1]
        confirm_btn.on_click(MagicMock())

        save_mock.assert_called_once()
        saved_arg = save_mock.call_args[0][0]
        assert saved_arg.descripcion == "Farmashop"
        assert saved_arg.monto == Decimal("320")


