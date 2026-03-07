"""
Tests para OCRService.
Usan mocks de pytesseract y PIL — no requieren Tesseract instalado ni imágenes reales.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import services.infrastructure.ocr_service as ocr_module
from result import Err, Ok

from models.ticket_model import PartialExpense
from services.infrastructure.ocr_service import OCRService


@pytest.fixture
def ocr_service():
    return OCRService()


@pytest.fixture
def datos_tesseract_validos():
    """Simula salida de pytesseract.image_to_data() con un ticket legible."""
    return {
        "text": ["", "Tienda", "Inglesa", "", "Leche", "$", "120", "Total", "$1250"],
        "conf": [-1, 92, 88, -1, 85, 90, 91, 87, 93, -1],
    }


@pytest.fixture
def datos_tesseract_ilegibles():
    """Simula la salida de pytesseract para una imagen de mala calidad."""
    return {
        "text": ["", "   ", ""],
        "conf": [-1, 10, -1],
    }


class TestOCRServiceExtraerTexto:

    async def test_archivo_no_existe_retorna_error(self, ocr_service):
        resultado = await ocr_service.extraer_texto("/ruta/inexistente/ticket.jpg")

        assert isinstance(resultado, Err)
        assert "no encontrada" in resultado.err().message

    async def test_imagen_valida_retorna_texto_y_confianza(
        self, datos_tesseract_validos
    ):
        import pathlib
        ocr = OCRService()
        mock_img = MagicMock()

        with (
            patch.object(ocr_module.Image, "open", return_value=mock_img),
            patch.object(ocr, "_preprocesar_imagen", return_value=mock_img),
            patch.object(
                ocr_module.pytesseract,
                "image_to_data",
                return_value=datos_tesseract_validos,
            ),
            patch.object(pathlib.Path, "exists", return_value=True),
        ):
            resultado = await ocr.extraer_texto("/fake/ticket.jpg")

        assert isinstance(resultado, Ok)
        partial = resultado.ok()
        assert isinstance(partial, PartialExpense)
        assert "Tienda" in partial.texto_crudo
        assert partial.confianza_ocr > 0.0
        assert partial.imagen_path == "/fake/ticket.jpg"

    async def test_imagen_ilegible_retorna_confianza_cero(
        self, datos_tesseract_ilegibles
    ):
        import pathlib
        ocr = OCRService()
        mock_img = MagicMock()

        with (
            patch.object(ocr_module.Image, "open", return_value=mock_img),
            patch.object(ocr, "_preprocesar_imagen", return_value=mock_img),
            patch.object(
                ocr_module.pytesseract,
                "image_to_data",
                return_value=datos_tesseract_ilegibles,
            ),
            patch.object(pathlib.Path, "exists", return_value=True),
        ):
            resultado = await ocr.extraer_texto("/fake/ticket_borroso.jpg")

        assert isinstance(resultado, Ok)
        partial = resultado.ok()
        assert partial.confianza_ocr == 0.0

    async def test_pytesseract_no_instalado_retorna_error(
        self, ocr_service, tmp_path
    ):
        imagen_path = tmp_path / "ticket.jpg"
        imagen_path.write_bytes(b"fake_image_data")

        with patch("services.infrastructure.ocr_service._TESSERACT_DISPONIBLE", False):
            resultado = await ocr_service.extraer_texto(str(imagen_path))

        assert isinstance(resultado, Err)
        assert "pytesseract" in resultado.err().message

    async def test_error_inesperado_retorna_err(self, ocr_service, tmp_path):
        imagen_path = tmp_path / "ticket.jpg"
        imagen_path.write_bytes(b"fake_image_data")

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch.object(ocr_module.Image, "open", side_effect=OSError("corrupto")),
        ):
            resultado = await ocr_service.extraer_texto(str(imagen_path))

        assert isinstance(resultado, Err)
        assert "Error OCR" in resultado.err().message


class TestPartialExpensePropiedades:

    def test_es_confiable_sobre_umbral(self):
        partial = PartialExpense(confianza_ocr=0.75)
        assert partial.es_confiable is True

    def test_es_confiable_bajo_umbral(self):
        partial = PartialExpense(confianza_ocr=0.3)
        assert partial.es_confiable is False

    def test_es_confiable_en_el_limite(self):
        partial = PartialExpense(confianza_ocr=0.5)
        assert partial.es_confiable is True

    def test_tiene_datos_minimos_con_monto(self):
        partial = PartialExpense(monto=1250.0)
        assert partial.tiene_datos_minimos is True

    def test_tiene_datos_minimos_con_comercio(self):
        partial = PartialExpense(comercio="Tienda Inglesa")
        assert partial.tiene_datos_minimos is True

    def test_tiene_datos_minimos_sin_datos(self):
        partial = PartialExpense()
        assert partial.tiene_datos_minimos is False

    def test_partial_expense_valores_por_defecto(self):
        partial = PartialExpense()
        assert partial.monto is None
        assert partial.fecha is None
        assert partial.comercio is None
        assert partial.items == []
        assert partial.categoria_sugerida is None
        assert partial.confianza_ocr == 0.0
        assert partial.texto_crudo == ""
        assert partial.imagen_path == ""
