"""
Tests para IAMemoryService, EmbeddingService y MemoryEventHandler.
Usa mocks para no depender de Ollama ni PostgreSQL.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from result import Err, Ok

from core.events import Event, EventSystem, EventType
from services.embedding_service import EmbeddingService
from services.ia_memory_service import IAMemoryService
from services.memory_event_handler import MemoryEventHandler


FAKE_EMBEDDING = [0.1] * 768


@pytest.fixture
def mock_embedding_service():
    svc = MagicMock(spec=EmbeddingService)
    svc.generar_embedding = AsyncMock(return_value=Ok(FAKE_EMBEDDING))
    return svc


@pytest.fixture
def mock_memoria_repo():
    repo = MagicMock()
    repo.guardar = MagicMock(return_value=42)
    repo.buscar_similares = MagicMock(return_value=[
        {"id": 1, "content": "Gasto en supermercado $1500", "source_type": "gasto_creado", "source_id": 10, "distance": 0.1},
        {"id": 2, "content": "Compra en carnicería $800", "source_type": "gasto_creado", "source_id": 11, "distance": 0.2},
    ])
    repo.count = MagicMock(return_value=2)
    return repo


@pytest.fixture
def memory_service(mock_memoria_repo, mock_embedding_service):
    return IAMemoryService(mock_memoria_repo, mock_embedding_service)


class TestIAMemoryService:
    @pytest.mark.asyncio
    async def test_registrar_evento_contable_ok(self, memory_service, mock_embedding_service, mock_memoria_repo):
        result = await memory_service.registrar_evento_contable(
            texto_plano="Gasto de $1000 en supermercado",
            source_type="gasto_creado",
            source_id=5,
        )
        assert isinstance(result, Ok)
        assert result.ok() == 42
        mock_embedding_service.generar_embedding.assert_called_once_with(
            "Gasto de $1000 en supermercado"
        )
        mock_memoria_repo.guardar.assert_called_once()

    @pytest.mark.asyncio
    async def test_registrar_texto_vacio_devuelve_err(self, memory_service):
        result = await memory_service.registrar_evento_contable(texto_plano="")
        assert isinstance(result, Err)

    @pytest.mark.asyncio
    async def test_registrar_falla_si_embedding_falla(self, mock_memoria_repo):
        svc_fallido = MagicMock(spec=EmbeddingService)
        svc_fallido.generar_embedding = AsyncMock(
            return_value=Err(MagicMock(message="Ollama no disponible"))
        )
        memory_service = IAMemoryService(mock_memoria_repo, svc_fallido)
        result = await memory_service.registrar_evento_contable("Texto válido")
        assert isinstance(result, Err)
        mock_memoria_repo.guardar.assert_not_called()

    @pytest.mark.asyncio
    async def test_buscar_contexto_para_pregunta(self, memory_service, mock_embedding_service):
        result = await memory_service.buscar_contexto_para_pregunta(
            pregunta="¿En qué gasté en alimentos?"
        )
        assert isinstance(result, Ok)
        contextos = result.ok()
        assert len(contextos) == 2
        assert "supermercado" in contextos[0]
        mock_embedding_service.generar_embedding.assert_called_once()

    @pytest.mark.asyncio
    async def test_buscar_sin_memoria_devuelve_lista_vacia(self, mock_embedding_service):
        repo_vacio = MagicMock()
        repo_vacio.buscar_similares = MagicMock(return_value=[])
        repo_vacio.count = MagicMock(return_value=0)
        svc = IAMemoryService(repo_vacio, mock_embedding_service)
        result = await svc.buscar_contexto_para_pregunta("cualquier pregunta")
        assert isinstance(result, Ok)
        assert result.ok() == []

    @pytest.mark.asyncio
    async def test_contexto_respeta_limite_chars(self, mock_embedding_service):
        texto_largo = "X" * 10000
        repo = MagicMock()
        repo.buscar_similares = MagicMock(return_value=[
            {"id": i, "content": texto_largo, "source_type": "gasto_creado", "source_id": i, "distance": 0.1}
            for i in range(5)
        ])
        repo.count = MagicMock(return_value=5)
        svc = IAMemoryService(repo, mock_embedding_service)
        result = await svc.buscar_contexto_para_pregunta("pregunta", limit=5)
        assert isinstance(result, Ok)
        total_chars = sum(len(c) for c in result.ok())
        assert total_chars <= 15000

    def test_tiene_memoria(self, memory_service):
        assert memory_service.tiene_memoria() is True

    def test_no_tiene_memoria_si_count_cero(self, mock_embedding_service):
        repo = MagicMock()
        repo.count = MagicMock(return_value=0)
        svc = IAMemoryService(repo, mock_embedding_service)
        assert svc.tiene_memoria() is False


class TestMemoryEventHandler:
    @pytest.mark.asyncio
    async def test_handle_gasto_creado(self, mock_memoria_repo, mock_embedding_service):
        memory_service = IAMemoryService(mock_memoria_repo, mock_embedding_service)
        handler = MemoryEventHandler(memory_service)
        event = Event(
            type=EventType.GASTO_CREADO,
            familia_id=1,
            source_id=10,
            data={
                "descripcion": "UTE",
                "monto": 3500.0,
                "categoria": "🏠 Hogar",
                "metodo_pago": "Débito",
                "fecha": "2025-02-01",
            },
        )
        await handler.handle(event)
        mock_embedding_service.generar_embedding.assert_called_once()
        mock_memoria_repo.guardar.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_ingreso_creado(self, mock_memoria_repo, mock_embedding_service):
        memory_service = IAMemoryService(mock_memoria_repo, mock_embedding_service)
        handler = MemoryEventHandler(memory_service)
        event = Event(
            type=EventType.INGRESO_CREADO,
            familia_id=1,
            source_id=5,
            data={"descripcion": "Sueldo", "monto": 50000.0, "categoria": "sueldo", "fecha": "2025-02-01"},
        )
        await handler.handle(event)
        mock_embedding_service.generar_embedding.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_snapshot_creado_llama_embedding(self, mock_memoria_repo, mock_embedding_service):
        memory_service = IAMemoryService(mock_memoria_repo, mock_embedding_service)
        handler = MemoryEventHandler(memory_service)
        event = Event(
            type=EventType.SNAPSHOT_CREADO,
            familia_id=1,
            data={"categoria": "🛒 Almacén", "total_dinero": 5000, "cantidad_compras": 10, "ticket_promedio": 500, "mes": 2, "anio": 2025},
        )
        await handler.handle(event)
        mock_embedding_service.generar_embedding.assert_called_once()
        mock_memoria_repo.guardar.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_no_propaga_excepciones(self, mock_embedding_service):
        repo_roto = MagicMock()
        repo_roto.guardar = MagicMock(side_effect=Exception("DB explota"))
        svc_roto = MagicMock(spec=IAMemoryService)
        svc_roto.registrar_evento_contable = AsyncMock(side_effect=Exception("Error grave"))
        handler = MemoryEventHandler(svc_roto)
        event = Event(
            type=EventType.GASTO_CREADO,
            familia_id=1,
            data={"descripcion": "test", "monto": 100.0, "categoria": "X", "metodo_pago": "efectivo", "fecha": "2025-01-01"},
        )
        await handler.handle(event)


class TestEventSystem:
    @pytest.mark.asyncio
    async def test_subscribe_y_publish(self):
        sistema = EventSystem()
        llamadas = []

        async def handler(event: Event):
            llamadas.append(event.type)

        sistema.subscribe(EventType.GASTO_CREADO, handler)
        await sistema.publish(Event(type=EventType.GASTO_CREADO, familia_id=1, data={}))
        assert llamadas == [EventType.GASTO_CREADO]

    @pytest.mark.asyncio
    async def test_handler_con_error_no_rompe_otros(self):
        sistema = EventSystem()
        resultados = []

        async def handler_malo(event: Event):
            raise ValueError("Error intencional")

        async def handler_bueno(event: Event):
            resultados.append("ok")

        sistema.subscribe(EventType.GASTO_CREADO, handler_malo)
        sistema.subscribe(EventType.GASTO_CREADO, handler_bueno)
        await sistema.publish(Event(type=EventType.GASTO_CREADO, familia_id=1, data={}))
        assert resultados == ["ok"]

    @pytest.mark.asyncio
    async def test_sin_handlers_no_falla(self):
        sistema = EventSystem()
        await sistema.publish(Event(type=EventType.GASTO_CREADO, familia_id=1, data={}))

    def test_clear_elimina_handlers(self):
        sistema = EventSystem()

        async def handler(event: Event):
            pass

        sistema.subscribe(EventType.GASTO_CREADO, handler)
        sistema.clear()
        assert EventType.GASTO_CREADO not in sistema._handlers


class TestEmbeddingServiceMock:
    @pytest.mark.asyncio
    async def test_texto_vacio_devuelve_err(self):
        with patch("httpx.AsyncClient") as _:
            svc = EmbeddingService()
            result = await svc.generar_embedding("")
            assert isinstance(result, Err)

    @pytest.mark.asyncio
    async def test_texto_demasiado_largo_se_trunca(self):
        texto_largo = "A" * 10000
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"embedding": FAKE_EMBEDDING}
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
                post=AsyncMock(return_value=mock_response)
            ))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
            svc = EmbeddingService()
            result = await svc.generar_embedding(texto_largo)
            assert isinstance(result, Ok)
