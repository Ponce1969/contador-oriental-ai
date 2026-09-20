"""Tests for Voice-to-Expense microservice (Faster-Whisper, NLP, and FastAPI)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from voice_api.main import (
    JobStore,
    app,
    process_voice_expense,
)
from voice_api.models import JobStatus, VoiceExpenseResponse
from voice_api.nlp import (
    _parse_colloquial_amount,
    extract_expense_regex_fallback,
    parse_expense_with_ollama,
)

# ===========================================================================
# 1. Unit Tests: Uruguayan Colloquial Amounts and Numbers
# ===========================================================================


class TestColloquialAmountParsing:
    """Tests for _parse_colloquial_amount behavior."""

    @pytest.mark.parametrize(
        ("input_text", "expected_amount"),
        [
            ("dos lucas", Decimal("2000")),
            ("tres palos", Decimal("3000")),
            ("5 lucas", Decimal("5000")),
            ("10 palos", Decimal("10000")),
            ("una gamba", Decimal("100")),
            ("tres gambas", Decimal("300")),
            ("450 pesos", Decimal("450")),
            ("$ 1250", Decimal("1250")),
            ("350.50 pesos", Decimal("350.50")),
            ("gasté 1200 en Devoto", Decimal("1200")),
        ],
    )
    def test_parses_valid_colloquial_and_numeric_amounts(
        self, input_text: str, expected_amount: Decimal
    ):
        result = _parse_colloquial_amount(input_text)
        assert result == expected_amount

    def test_returns_none_when_no_amount_present(self):
        result = _parse_colloquial_amount("fui a caminar por la rambla")
        assert result is None


# ===========================================================================
# 2. Unit Tests: Uruguayan Regex Fallback Extractor
# ===========================================================================


class TestRegexFallbackExtraction:
    """Tests for extract_expense_regex_fallback."""

    def test_extracts_supermarket_expense_with_debit(self):
        text = "gasté 1500 pesos en Disco pagué con débito"
        data = extract_expense_regex_fallback(text)

        assert data["monto"] == Decimal("1500")
        assert data["currency"] == "UYU"
        assert data["comercio"] == "Disco"
        assert data["categoria"] == "🛒 Almacén"
        assert data["subcategoria"] == "Supermercado"
        assert data["medio_pago"] == "Débito"
        assert data["engine_used"] == "regex-uruguay-fallback"

    def test_extracts_fuel_expense_at_ancap(self):
        text = "cargué dos lucas de nafta en Ancap con oca"
        data = extract_expense_regex_fallback(text)

        assert data["monto"] == Decimal("2000")
        assert data["currency"] == "UYU"
        assert data["comercio"] == "Ancap"
        assert data["categoria"] == "🚗 Vehículos"
        assert data["subcategoria"] == "Combustible"
        assert data["medio_pago"] == "Oca"

    def test_extracts_pharmacy_expense_at_farmashop(self):
        text = "compré remedios en Farmashop 800 pesos en efectivo"
        data = extract_expense_regex_fallback(text)

        assert data["monto"] == Decimal("800")
        assert data["currency"] == "UYU"
        assert data["comercio"] == "Farmashop"
        assert data["categoria"] == "👨‍⚕️ Salud"
        assert data["subcategoria"] == "Farmacia"
        assert data["medio_pago"] == "Efectivo"

    def test_detects_usd_currency(self):
        text = "pagué 45 dolares de una remera en zara"
        data = extract_expense_regex_fallback(text)

        assert data["monto"] == Decimal("45")
        assert data["currency"] == "USD"

    def test_returns_empty_dict_on_empty_text(self):
        assert extract_expense_regex_fallback("") == {}


# ===========================================================================
# 3. Unit Tests: Ollama Gemma 2:2b NLP Parser
# ===========================================================================


class TestOllamaParser:
    """Tests for parse_expense_with_ollama with mocked HTTP interactions."""

    @pytest.mark.asyncio
    async def test_successful_ollama_parsing(self):
        mock_ollama_json = {
            "response": (
                '{"monto": 850.0, "currency": "UYU", "comercio": "Devoto", '
                '"categoria": "🛒 Almacén", "subcategoria": "Supermercado", '
                '"medio_pago": "Débito", "notas": "Compra de verduras"}'
            )
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_ollama_json
        mock_resp.raise_for_status.return_value = None

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            result = await parse_expense_with_ollama("850 pesos en devoto con debito")

        assert result is not None
        assert result["monto"] == Decimal("850.0")
        assert result["currency"] == "UYU"
        assert result["comercio"] == "Devoto"
        assert result["categoria"] == "🛒 Almacén"
        assert result["medio_pago"] == "Débito"
        assert result["confidence"] == 0.95
        assert "ollama" in result["engine_used"]

    @pytest.mark.asyncio
    async def test_returns_none_on_invalid_json(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": "No pude entender el gasto"}
        mock_resp.raise_for_status.return_value = None

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            result = await parse_expense_with_ollama("audio confuso")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_http_error(self):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = RuntimeError("Connection refused")
            result = await parse_expense_with_ollama("gasto de prueba")

        assert result is None


# ===========================================================================
# 4. Unit Tests: JobStore
# ===========================================================================


class TestJobStore:
    """Tests for in-memory JobStore lifecycle and TTL cleanup."""

    def test_create_and_retrieve_job(self):
        store = JobStore()
        job = store.create("job-123")

        assert job.job_id == "job-123"
        assert job.status == JobStatus.PENDING

        retrieved = store.get("job-123")
        assert retrieved is not None
        assert retrieved.job_id == "job-123"

    def test_update_job_status_and_result(self):
        store = JobStore()
        store.create("job-456")

        res = VoiceExpenseResponse(
            success=True,
            text="dos lucas en ancap",
            monto=Decimal("2000"),
            currency="UYU",
        )
        updated = store.update("job-456", status=JobStatus.COMPLETED, resultado=res)

        assert updated.status == JobStatus.COMPLETED
        assert updated.resultado is not None
        assert updated.resultado.monto == Decimal("2000")

    def test_active_jobs_count(self):
        store = JobStore()
        store.create("j1")
        store.create("j2")
        store.update("j1", status=JobStatus.PROCESSING)
        assert store.active_jobs_count() == 2

        store.update("j2", status=JobStatus.COMPLETED)
        assert store.active_jobs_count() == 1

    def test_cleanup_expired_jobs(self):
        store = JobStore()
        rec = store.create("old-job")
        rec.created_at = datetime.now(UTC) - timedelta(seconds=600)

        store.create("fresh-job")

        purged = store.cleanup(ttl_seconds=300)
        assert purged == 1
        assert store.get("old-job") is None
        assert store.get("fresh-job") is not None


# ===========================================================================
# 5. Pipeline & FastAPI Endpoints Tests
# ===========================================================================


class TestVoicePipeline:
    """Tests for process_voice_expense pipeline."""

    @pytest.mark.asyncio
    async def test_process_voice_expense_falls_back_to_regex(self, tmp_path):
        dummy_audio = tmp_path / "voice.wav"
        dummy_audio.write_bytes(b"dummy_riff_header")

        with (
            patch(
                "voice_api.main._run_transcription",
                return_value=("dos lucas en ancap con oca", "es", 2.5),
            ),
            patch("voice_api.main.parse_expense_with_ollama", return_value=None),
        ):
            resp = await process_voice_expense(dummy_audio)

        assert resp.success is True
        assert resp.text == "dos lucas en ancap con oca"
        assert resp.monto == Decimal("2000")
        assert resp.comercio == "Ancap"
        assert resp.categoria == "🚗 Vehículos"
        assert "regex-uruguay-fallback" in resp.engine_used

    @pytest.mark.asyncio
    async def test_process_voice_expense_empty_transcription(self, tmp_path):
        dummy_audio = tmp_path / "silence.wav"
        dummy_audio.write_bytes(b"silence")

        with patch("voice_api.main._run_transcription", return_value=("", "es", 0.0)):
            resp = await process_voice_expense(dummy_audio)

        assert resp.success is False
        assert "No se detectó voz" in (resp.error or "")


class TestVoiceAPIEndpoints:
    """Tests for FastAPI HTTP endpoints."""

    def test_health_endpoint(self):
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "model" in data
        assert "active_jobs" in data

    def test_voice_upload_form_endpoint(self):
        client = TestClient(app)
        resp = client.get("/voice-upload-form?session_id=sess-abc")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "sess-abc" in resp.text

    def test_voice_resultado_polling(self):
        client = TestClient(app)
        resp = client.get("/voice-resultado/non-existent")
        assert resp.status_code == 200
        assert resp.json() == {"ready": False}
