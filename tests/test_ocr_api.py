"""Tests for hybrid OCR microservice (Gemini 2.0 Flash and local fallback)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ocr_api.config import settings
from ocr_api.main import (
    extraer_con_gemini_flash,
    procesar_job_async,
)


@pytest.fixture
def fake_receipt_bytes() -> bytes:
    """Minimal fake image bytes for testing."""
    return b"fake_jpeg_data"


class TestGeminiFlashExtraction:
    """Tests for extraer_con_gemini_flash function."""

    async def test_extraer_con_gemini_flash_success(self, fake_receipt_bytes):
        mock_response_data = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": (
                                    '{"monto": 1450.5, "fecha": "2026-03-01", '
                                    '"comercio": "Devoto", "items": ["yerba", "cafe"], '
                                    '"currency": "UYU"}'
                                )
                            }
                        ]
                    }
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response_data
        mock_resp.raise_for_status.return_value = None

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            data = await extraer_con_gemini_flash(
                image_bytes=fake_receipt_bytes,
                api_key="test-api-key",
                model="gemini-2.0-flash",
            )

        assert data is not None
        assert data["monto"] == 1450.5
        assert data["fecha"] == "2026-03-01"
        assert data["comercio"] == "Devoto"
        assert data["items"] == ["yerba", "cafe"]
        assert data["currency"] == "UYU"

    async def test_extraer_con_gemini_flash_empty_response(self, fake_receipt_bytes):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"candidates": []}
        mock_resp.raise_for_status.return_value = None

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            data = await extraer_con_gemini_flash(
                image_bytes=fake_receipt_bytes,
                api_key="test-api-key",
                model="gemini-2.0-flash",
            )

        assert data is None

    async def test_extraer_con_gemini_flash_http_error(self, fake_receipt_bytes):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = RuntimeError("Network error")
            data = await extraer_con_gemini_flash(
                image_bytes=fake_receipt_bytes,
                api_key="test-api-key",
                model="gemini-2.0-flash",
            )

        assert data is None


class TestProcesarJobAsync:
    """Tests for job processing routing with hybrid engines."""

    async def test_cloud_engine_success(self, tmp_path):
        ticket_file = tmp_path / "ticket.jpg"
        ticket_file.write_bytes(b"receipt_image_bytes")

        gemini_result = {
            "monto": 890.0,
            "fecha": "2026-02-28",
            "comercio": "Disco",
            "items": ["leche", "arroz"],
            "currency": "UYU",
        }

        with (
            patch.object(settings, "gemini_api_key", "valid-key"),
            patch(
                "ocr_api.main.extraer_con_gemini_flash",
                new_callable=AsyncMock,
                return_value=gemini_result,
            ),
        ):
            resp = await procesar_job_async(ticket_file, engine="cloud")

        assert resp.success is True
        assert resp.engine_used == "gemini-2.0-flash"
        assert resp.monto == 890.0
        assert resp.comercio == "Disco"
        assert resp.currency == "UYU"

    async def test_cloud_engine_missing_key_returns_error(self, tmp_path):
        ticket_file = tmp_path / "ticket.jpg"
        ticket_file.write_bytes(b"receipt_image_bytes")

        with patch.object(settings, "gemini_api_key", None):
            resp = await procesar_job_async(ticket_file, engine="cloud")

        assert resp.success is False
        assert "no configurada" in (resp.error or "")
        assert resp.engine_used == "gemini-2.0-flash"

    async def test_auto_engine_falls_back_to_local_on_cloud_failure(self, tmp_path):
        ticket_file = tmp_path / "ticket.jpg"
        ticket_file.write_bytes(b"receipt_image_bytes")

        local_ocr_text = "Tienda Inglesa 2026-03-01 Total 500"
        local_parsed = {
            "monto": 500.0,
            "fecha": "2026-03-01",
            "comercio": "Tienda Inglesa",
            "items": ["galletitas"],
            "currency": "UYU",
        }

        with (
            patch.object(settings, "gemini_api_key", "valid-key"),
            patch(
                "ocr_api.main.extraer_con_gemini_flash",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Cloud timeout"),
            ),
            patch(
                "ocr_api.main.extraer_texto_tesseract",
                new_callable=AsyncMock,
                return_value=(local_ocr_text, 0.85),
            ),
            patch(
                "ocr_api.main.parsear_con_ollama",
                new_callable=AsyncMock,
                return_value=local_parsed,
            ),
        ):
            resp = await procesar_job_async(ticket_file, engine="auto")

        assert resp.success is True
        assert resp.engine_used == "local-tesseract"
        assert resp.monto == 500.0
        assert resp.comercio == "Tienda Inglesa"

    async def test_local_engine_bypasses_gemini(self, tmp_path):
        ticket_file = tmp_path / "ticket.jpg"
        ticket_file.write_bytes(b"receipt_image_bytes")

        mock_gemini = AsyncMock()

        local_ocr_text = "TaTa 2026-03-02 Total 300"
        local_parsed = {
            "monto": 300.0,
            "fecha": "2026-03-02",
            "comercio": "TaTa",
            "items": ["pan"],
            "currency": "UYU",
        }

        with (
            patch.object(settings, "gemini_api_key", "valid-key"),
            patch("ocr_api.main.extraer_con_gemini_flash", mock_gemini),
            patch(
                "ocr_api.main.extraer_texto_tesseract",
                new_callable=AsyncMock,
                return_value=(local_ocr_text, 0.90),
            ),
            patch(
                "ocr_api.main.parsear_con_ollama",
                new_callable=AsyncMock,
                return_value=local_parsed,
            ),
        ):
            resp = await procesar_job_async(ticket_file, engine="local")

        assert mock_gemini.called is False
        assert resp.success is True
        assert resp.engine_used == "local-tesseract"
        assert resp.monto == 300.0
        assert resp.comercio == "TaTa"
