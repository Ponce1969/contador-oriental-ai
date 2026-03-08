"""
Tests para TicketService.
Usan mocks de OCRService, AIAdvisorService y ExpenseRepository.
No requieren Tesseract, Ollama ni base de datos.
"""
from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from result import Err, Ok

from models.errors import AppError
from models.ticket_model import PartialExpense
from services.infrastructure.ticket_service import TicketService


@pytest.fixture
def mock_ocr():
    return AsyncMock()


@pytest.fixture
def mock_embedding():
    return AsyncMock()


@pytest.fixture
def mock_expense_repo():
    return MagicMock()


@pytest.fixture
def mock_ai():
    return AsyncMock()


@pytest.fixture
def ticket_service(mock_ocr, mock_embedding, mock_expense_repo, mock_ai):
    return TicketService(
        ocr_service=mock_ocr,
        embedding_service=mock_embedding,
        expense_repo=mock_expense_repo,
        ai_service=mock_ai,
    )


@pytest.fixture
def partial_con_texto():
    return PartialExpense(
        texto_crudo="TIENDA INGLESA RUT 12345 Leche 120 Pan 85 TOTAL 1250",
        confianza_ocr=0.85,
        imagen_path="/fake/ticket.jpg",
    )


class TestTicketServiceProcesarTicket:

    async def test_ocr_falla_retorna_err(self, ticket_service, mock_ocr):
        mock_ocr.extraer_texto.return_value = Err(AppError("imagen no encontrada"))

        resultado = await ticket_service.procesar_ticket("/fake/ticket.jpg")

        assert isinstance(resultado, Err)
        assert "imagen no encontrada" in resultado.err().message

    async def test_flujo_completo_con_mocks(
        self, ticket_service, mock_ocr, mock_ai,
        mock_embedding, mock_expense_repo, partial_con_texto
    ):
        mock_ocr.extraer_texto.return_value = Ok(partial_con_texto)
        mock_ai.llamada_directa.return_value = (
            '{"monto": 1250.0, "fecha": "2026-02-28", '
            '"comercio": "Tienda Inglesa", "items": ["leche", "pan"]}'
        )
        mock_embedding.generar_embedding.return_value = Ok([0.1] * 768)
        mock_gasto = MagicMock()
        mock_gasto.categoria.value = "🛒 Almacén"
        mock_expense_repo.buscar_por_similitud.return_value = [
            (mock_gasto, 0.92)
        ]

        resultado = await ticket_service.procesar_ticket("/fake/ticket.jpg")

        assert isinstance(resultado, Ok)
        partial = resultado.ok()
        assert partial.monto == 1250.0
        assert partial.comercio == "Tienda Inglesa"
        assert partial.items == ["leche", "pan"]
        assert partial.fecha == date(2026, 2, 28)
        assert partial.categoria_sugerida == "🛒 Almacén"

    async def test_gemma_falla_retorna_partial_sin_datos(
        self, ticket_service, mock_ocr, mock_ai, mock_embedding,
        mock_expense_repo, partial_con_texto
    ):
        mock_ocr.extraer_texto.return_value = Ok(partial_con_texto)
        mock_ai.llamada_directa.return_value = ""
        mock_embedding.generar_embedding.return_value = Err(AppError("sin embedding"))

        resultado = await ticket_service.procesar_ticket("/fake/ticket.jpg")

        assert isinstance(resultado, Ok)
        partial = resultado.ok()
        assert partial.monto is None
        assert partial.comercio is None
        assert partial.categoria_sugerida is None
        assert partial.texto_crudo != ""  # el texto crudo siempre está

    async def test_confianza_baja_loguea_warning(
        self, ticket_service, mock_ocr, mock_ai, mock_embedding,
        mock_expense_repo, caplog
    ):
        partial_baja = PartialExpense(
            texto_crudo="texto ilegible",
            confianza_ocr=0.15,
        )
        mock_ocr.extraer_texto.return_value = Ok(partial_baja)
        mock_ai.llamada_directa.return_value = ""
        mock_embedding.generar_embedding.return_value = Err(AppError("x"))

        with caplog.at_level("WARNING"):
            await ticket_service.procesar_ticket("/fake/ticket.jpg")

        assert "Confianza OCR baja" in caplog.text


class TestTicketServiceParsearConGemma:

    async def test_json_valido_retorna_datos(self, ticket_service, mock_ai):
        mock_ai.llamada_directa.return_value = (
            '{"monto": 500.0, "fecha": "2026-01-15", '
            '"comercio": "Disco", "items": ["arroz"]}'
        )
        resultado = await ticket_service._parsear_con_gemma("texto ticket")

        assert resultado is not None
        assert resultado["monto"] == 500.0
        assert resultado["comercio"] == "Disco"

    async def test_gemma_con_texto_extra_extrae_json(
        self, ticket_service, mock_ai
    ):
        mock_ai.llamada_directa.return_value = (
            "Acá está el resultado: "
            '{"monto": 750.0, "fecha": null, "comercio": "Devoto", "items": []}'
            " Espero que sirva."
        )
        resultado = await ticket_service._parsear_con_gemma("texto ticket")

        assert resultado is not None
        assert resultado["monto"] == 750.0
        assert resultado["comercio"] == "Devoto"

    async def test_json_invalido_retorna_none(self, ticket_service, mock_ai):
        mock_ai.llamada_directa.return_value = "No encontré datos en el ticket."

        resultado = await ticket_service._parsear_con_gemma("texto ticket")

        assert resultado is None

    async def test_respuesta_vacia_retorna_none(self, ticket_service, mock_ai):
        mock_ai.llamada_directa.return_value = ""

        resultado = await ticket_service._parsear_con_gemma("texto ticket")

        assert resultado is None

    async def test_texto_vacio_retorna_none(self, ticket_service, mock_ai):
        resultado = await ticket_service._parsear_con_gemma("")

        assert resultado is None
        mock_ai.llamada_directa.assert_not_called()


class TestTicketServiceSugerirCategoria:

    async def test_retorna_categoria_mas_frecuente(
        self, ticket_service, mock_embedding, mock_expense_repo
    ):
        mock_embedding.generar_embedding.return_value = Ok([0.1] * 768)
        mock_g1, mock_g2, mock_g3 = MagicMock(), MagicMock(), MagicMock()
        mock_g1.categoria.value = "🛒 Almacén"
        mock_g2.categoria.value = "🛒 Almacén"
        mock_g3.categoria.value = "🏠 Hogar"
        mock_expense_repo.buscar_por_similitud.return_value = [
            (mock_g1, 0.95), (mock_g2, 0.90), (mock_g3, 0.80)
        ]

        resultado = await ticket_service._sugerir_categoria("supermercado")

        assert resultado == "🛒 Almacén"

    async def test_embedding_falla_retorna_none(
        self, ticket_service, mock_embedding
    ):
        mock_embedding.generar_embedding.return_value = Err(AppError("Ollama down"))

        resultado = await ticket_service._sugerir_categoria("supermercado")

        assert resultado is None

    async def test_sin_resultados_retorna_none(
        self, ticket_service, mock_embedding, mock_expense_repo
    ):
        mock_embedding.generar_embedding.return_value = Ok([0.1] * 768)
        mock_expense_repo.buscar_por_similitud.return_value = []

        resultado = await ticket_service._sugerir_categoria("algo raro")

        assert resultado is None
