"""Tests for hybrid OCR microservice (Gemini 2.0 Flash and local fallback)."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ocr_api.config import settings
from ocr_api.main import (
    _group_rapidocr_lines,
    _resize_for_ocr,
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
        mock_resp.status_code = 200
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
        mock_resp.status_code = 200
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
        assert resp.engine_used.startswith("local-tesseract")
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
        assert resp.engine_used.startswith("local-tesseract")
        assert resp.monto == 300.0
        assert resp.comercio is not None and resp.comercio.lower() == "tata"

    async def test_local_engine_regex_fallback_when_ollama_fails(self, tmp_path):
        ticket_file = tmp_path / "ticket.jpg"
        ticket_file.write_bytes(b"receipt_image_bytes")

        ticket_text = (
            "SUPERMERCADO DEVOTO\n"
            "RUT 219999990019\n"
            "FECHA: 15/08/2026 14:30\n"
            "YERBA CANARIAS 1KG  250.00\n"
            "LECHE CONAPROLE      45.00\n"
            "TOTAL $ 295,00\n"
        )

        with (
            patch(
                "ocr_api.main.extraer_texto_tesseract",
                new_callable=AsyncMock,
                return_value=(ticket_text, 0.88),
            ),
            patch(
                "ocr_api.main.parsear_con_ollama",
                new_callable=AsyncMock,
                return_value=None,  # Ollama fails / timeout
            ),
        ):
            resp = await procesar_job_async(ticket_file, engine="local")

        assert resp.success is True
        assert resp.engine_used == "local-tesseract-regex"
        assert resp.monto == 295.0
        assert resp.comercio == "Devoto"
        assert str(resp.fecha) == "2026-08-15"
        assert resp.currency == "UYU"

    async def test_local_engine_rejects_hallucinated_values_from_ollama(self, tmp_path):
        ticket_file = tmp_path / "ticket_pantalon.jpg"
        ticket_file.write_bytes(b"ticket_bytes")

        ticket_text = (
            "TIENDA URUGUAY\n"
            "FECHA: 05/09/2026\n"
            "PANTALON FELPA 790,00\n"
            "TOTAL A PAGAR: $ 790,00\n"
        )
        # Ollama alucina los valores del ejemplo anterior (1250 y leche/pan/aceite)
        hallucinated_ollama = {
            "monto": 1250.0,
            "fecha": "2026-02-28",
            "comercio": "Tienda Inglesa",
            "items": ["leche", "pan", "aceite"],
            "currency": None,
        }

        with (
            patch.object(settings, "gemini_api_key", None),
            patch(
                "ocr_api.main.extraer_texto_tesseract",
                new_callable=AsyncMock,
                return_value=(ticket_text, 0.88),
            ),
            patch(
                "ocr_api.main.parsear_con_ollama",
                new_callable=AsyncMock,
                return_value=hallucinated_ollama,
            ),
        ):
            resp = await procesar_job_async(ticket_file, engine="local")

        assert resp.success is True
        # El monto alucinado (1250) se descarta por el real del ticket (790)
        assert resp.monto == 790.0
        assert "leche" not in resp.items
        assert "pan" not in resp.items


class TestRegexExtraction:
    """Direct tests for Uruguayan regex fallback parser."""

    def test_extraer_datos_regex_with_pesos_ticket(self):
        from ocr_api.main import extraer_datos_regex

        texto = (
            "TATA S.A.\n"
            "RUT: 210001230018\n"
            "FECHA 28/02/2026\n"
            "SUBTOTAL 1.200,00\n"
            "TOTAL A PAGAR: $ 1.250,50\n"
        )
        data = extraer_datos_regex(texto)
        assert data["comercio"] == "Tata"
        assert data["fecha"] == "2026-02-28"
        assert data["monto"] == 1250.5
        assert data["currency"] == "UYU"

    def test_extraer_datos_regex_with_usd_ticket(self):
        from ocr_api.main import extraer_datos_regex

        texto = (
            "AGROPECUARIA DEL SUR\n"
            "FECHA: 2026-05-10\n"
            "SEMILLAS MAIZ  USD 450.00\n"
            "TOTAL USD 450.00\n"
        )
        data = extraer_datos_regex(texto)
        assert data["comercio"] == "Agropecuaria"
        assert data["fecha"] == "2026-05-10"
        assert data["monto"] == 450.0
        assert data["currency"] == "USD"

    def test_extraer_datos_regex_rejects_upside_down_garbage(self):
        from ocr_api.main import extraer_datos_regex

        texto_upside_down = (
            "006. S 0110333\n"
            "O9Ya 30 SOOZN\n"
            "A XX A A ST Hr IE 1 cr\n"
            "pun; 19301 pepyueo\n"
            "( $ % JUAN IS IQ.)\n"
            "00'662 $ YV29VdA Y IVLOL\n"
            "WNINOvLI vd +34 NOTWLNVd\n"
            "VWWNI3 OANSNOO\n"
        )
        data = extraer_datos_regex(texto_upside_down)
        assert data["monto"] is None
        assert data["comercio"] is None
        assert data["items"] == []

    async def test_missing_monto_caps_confidence(self, tmp_path):
        ticket_file = tmp_path / "ticket.jpg"
        ticket_file.write_bytes(b"receipt_image_bytes")

        texto_sin_monto = "FARMACIA RIVERA\nFECHA 12/03/2026\nMEDICAMENTOS"

        with patch(
            "ocr_api.main.extraer_texto_tesseract",
            new_callable=AsyncMock,
            return_value=(texto_sin_monto, 0.88),
        ):
            resp = await procesar_job_async(ticket_file, engine="local")

        assert resp.monto is None
        assert resp.comercio == "Farmacia"
        # Confianza debe estar limitada si no hay monto detectado
        assert resp.confianza_ocr <= 0.35


class TestOplarosBenchmark:
    """Benchmark tests on real Uruguayan thermal receipt (OPLAROS S A)."""

    def test_oplaros_thermal_receipt_extraction(self):
        from ocr_api.main import extraer_datos_regex

        texto_oplaros = """
OPLAROS S A
18 DE JULIO 1423 MONTEVIDEO
RUT EMISOR 217887100012
DOCUMENTO e-TICKET
SERIE /Nº A 404640
FORMA DE PAGO Contado
CONSUMO FINAL
DATOS DEL CLIENTE
100 Generico
07/08/2026 UYU
DETALLES DE LA COMPRA IMPORTE
PANTALON FELPA ITAGUI M 1 UN 1.599,00 799,02
SUB TOTAL TASA BASICA $ 654,93
IVA TASA BASICA $ 144,08
TOTAL A PAGAR $ 799,00
MEDIOS DE PAGO
EFECTIVO $ 799,00
ADENDA
GRACIAS POR SU PREFERENCIA
"""
        data = extraer_datos_regex(texto_oplaros)

        # 1. Strict Decimal values
        assert data["monto"] == Decimal("799.00")
        assert data["subtotal"] == Decimal("654.93")
        assert data["tax"] == Decimal("144.08")
        assert data["line_amount"] == Decimal("799.02")
        assert data["payment_amount"] == Decimal("799.00")

        # 2. Metadata
        assert data["rut"] == "217887100012"
        assert data["document_type"] == "E-TICKET"
        assert data["currency"] == "UYU"
        assert data["fecha"] == "2026-08-07"
        assert data["comercio"] == "Oplaros"

        # 3. Arithmetic inconsistency preserved without mutating visual truth
        # 654.93 + 144.08 = 799.01 != 799.00
        assert data["arithmetic_consistent"] is False

        # 4. Decoupling: High visual legibility confidence despite arithmetic mismatch
        assert data["extraction_confidence"] >= Decimal("0.85")

    def test_oplaros_noisy_raw_tesseract_extraction(self):
        from ocr_api.main import extraer_datos_regex

        texto_real_server = """
e OMA AA
ra IA e
217887100012 - e TICKET
404640 Contado
PA DATOS DEL CUENTEN IACIADAN
100 Generico
a a Era
a EN
fe [oeoerattes pera comerse]
 PANTALON FELPA ITAGUM
ZHOSADIZOM 1 UN 22 159000 10902
SUB TOTAL TASA BASICA ; 654,83
IVA TASA BASICA 144,08
+, TOTAL A PAGAR $ . 799,00
- Descuento os - 0)
Cantidad Total: 1 Unid, 
MEDIOS DE PAGO
EFECTIVO 769,00 *
"""
        data = extraer_datos_regex(texto_real_server)
        assert data["monto"] == Decimal("799.00")
        assert data["subtotal"] == Decimal("654.83")
        assert data["tax"] == Decimal("144.08")
        assert data["rut"] == "217887100012"
        assert data["document_type"] in ("E-TICKET", "TICKET")

    def test_user_thermal_noisy_ocr_with_stray_artifacts(self):
        from ocr_api.main import extraer_datos_regex

        noisy_text = """o TE
: ies h
380 o 1428
Poe! 30 [ARNt DOCUMENT O:
: e-TICKET
CE PS .
Contado -.
q ACOMERAS 1 :
> PANTALON FELPA ITAGUÍM
210540126M' 1 "UN 22 1.599,00". 789/02
SUB TOTAL TASA BASICA. 5. a
IVA TASA BASICA -— 0. 900 144,08
TOTAL A PAGAR $ o 799,00
(Descuento
[ Cantidad ITosar ES
Él e MEDIOS DEPAGO
EFECTIVO LoS"""

        data = extraer_datos_regex(noisy_text)
        assert data["monto"] == Decimal("799.00")
        assert data["tax"] == Decimal("144.08")
        assert data["document_type"] == "E-TICKET"


class TestReceiptExtractorPort:
    """Tests for ReceiptExtractor Hexagonal Port and Adapter."""

    async def test_microservice_adapter_converts_to_receipt_extraction(self):
        from services.infrastructure.receipt_extractor_adapter import (
            MicroserviceReceiptExtractor,
        )

        adapter = MicroserviceReceiptExtractor(base_url="http://mock-ocr")

        mock_payload = {
            "success": True,
            "monto": "799.00",
            "subtotal": "654.93",
            "tax": "144.08",
            "comercio": "Oplaros",
            "rut": "217887100012",
            "document_type": "E-TICKET",
            "fecha": "2026-08-07",
            "currency": "UYU",
            "items": ["Pantalon Felpa Itagui"],
            "extraction_confidence": 0.90,
            "arithmetic_consistent": False,
            "engine_used": "local-tesseract-regex",
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload
        mock_resp.raise_for_status.return_value = None

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            result = await adapter.extract(b"fake_image_bytes")

        assert result.total == Decimal("799.00")
        assert result.subtotal == Decimal("654.93")
        assert result.tax == Decimal("144.08")
        assert result.rut == "217887100012"
        assert result.merchant == "Oplaros"
        assert result.arithmetic_consistent is False
        assert result.extraction_confidence == Decimal("0.90")
        assert len(result.items) == 1
        assert result.items[0].description == "Pantalon Felpa Itagui"


class TestRapidOCRIntegration:
    """Tests for RapidOCR (ONNX Runtime) ARM-optimized pipeline."""

    def test_resize_for_ocr_preserves_smaller_images(self):
        """Images smaller than max_dim should not be resized."""
        import numpy as np

        small_img = np.zeros((800, 600, 3), dtype=np.uint8)
        resized = _resize_for_ocr(small_img, max_dim=1920)
        assert resized.shape == (800, 600, 3)

    def test_resize_for_ocr_scales_down_large_images(self):
        """Images exceeding max_dim should scale down keeping aspect ratio."""
        import numpy as np

        # Foto típica de celular vertical de alta resolución (3840x2160)
        large_img = np.zeros((3840, 2160, 3), dtype=np.uint8)
        resized = _resize_for_ocr(large_img, max_dim=1920)
        h, w = resized.shape[:2]
        assert max(h, w) == 1920
        # Aspect ratio original 2160 / 3840 = 0.5625
        assert w == int(2160 * (1920 / 3840))

    def test_group_rapidocr_lines_preserves_horizontal_order(self):
        """Validates that items on the same horizontal line are sorted left-to-right."""
        # Dos cajas en la misma línea (y=100..120), pero desordenadas en x:
        # Caja A a la derecha (x=300..400): "$ 46.00"
        # Caja B a la izquierda (x=20..200): "LECHE CONAPROLE 1L"
        box_right = [[300, 100], [400, 100], [400, 120], [300, 120]]
        box_left = [[20, 102], [200, 102], [200, 122], [20, 122]]

        # Línea 2: Total abajo (y=200..220)
        box_total = [[20, 200], [250, 200], [250, 225], [20, 225]]

        raw_result = [
            [box_right, "$ 46.00", 0.95],
            [box_left, "LECHE CONAPROLE 1L", 0.98],
            [box_total, "TOTAL $ 46.00", 0.99],
        ]

        clean_text, conf = _group_rapidocr_lines(raw_result)
        lines = clean_text.splitlines()

        assert len(lines) == 2
        # La primera línea debe tener primero el concepto y luego el importe
        assert lines[0].startswith("LECHE CONAPROLE 1L")
        assert lines[0].endswith("$ 46.00")
        assert lines[1] == "TOTAL $ 46.00"
        assert conf > 0.90

    def test_group_rapidocr_lines_empty(self):
        """Empty or invalid result returns empty string and zero confidence."""
        assert _group_rapidocr_lines([]) == ("", 0.0)
        assert _group_rapidocr_lines(None) == ("", 0.0)

    async def test_rapidocr_primary_success(self, tmp_path):
        """RapidOCR is used as primary local engine when successful."""
        ticket_file = tmp_path / "ticket.jpg"
        ticket_file.write_bytes(b"receipt_image_bytes")

        mock_ocr_text = (
            "SUPERMERCADO DISCO\n"
            "RUT 210000000015\n"
            "FECHA 2026-03-10\n"
            "YERBA CANARIAS   $ 210.00\n"
            "TOTAL $ 210.00\n"
        )

        with (
            patch(
                "ocr_api.main.extraer_texto_rapidocr",
                new_callable=AsyncMock,
                return_value=(mock_ocr_text, 0.95),
            ),
            patch("ocr_api.main.extraer_texto_tesseract") as mock_tesseract,
        ):
            resp = await procesar_job_async(ticket_file, engine="local")

        assert resp.success is True
        assert resp.engine_used.startswith("local-rapidocr")
        assert resp.monto == 210.0
        assert resp.comercio == "Disco"
        assert str(resp.fecha) == "2026-03-10"
        # Tesseract NO debe haber sido llamado porque RapidOCR tuvo éxito
        assert mock_tesseract.called is False

    async def test_rapidocr_fallback_to_tesseract_when_empty(self, tmp_path):
        """When RapidOCR yields insufficient text, pipeline falls back to Tesseract."""
        ticket_file = tmp_path / "ticket.jpg"
        ticket_file.write_bytes(b"receipt_image_bytes")

        tesseract_text = (
            "SUPERMERCADO TATA\n"
            "FECHA: 12/03/2026\n"
            "PAN FLUIDO   $ 80.00\n"
            "TOTAL $ 80.00\n"
        )

        with (
            patch(
                "ocr_api.main.extraer_texto_rapidocr",
                new_callable=AsyncMock,
                return_value=("", 0.0),  # RapidOCR fails
            ),
            patch(
                "ocr_api.main.extraer_texto_tesseract",
                new_callable=AsyncMock,
                return_value=(tesseract_text, 0.85),
            ) as mock_tesseract,
        ):
            resp = await procesar_job_async(ticket_file, engine="local")

        assert resp.success is True
        assert resp.engine_used.startswith("local-tesseract")
        assert resp.monto == 80.0
        assert mock_tesseract.called is True
