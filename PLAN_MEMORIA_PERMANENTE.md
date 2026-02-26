# 🧠 Plan de Memoria Permanente - Contador Oriental AI

## 🎯 Visión General

Implementar un sistema de memoria vectorial RAG (Retrieval-Augmented Generation) para que el Contador Oriental tenga "memoria permanente" de los datos financieros, permitiendo búsquedas semánticas inteligentes y respuestas contextuales precisas.

---

## 🏗️ Arquitectura Propuesta

### **📚 Bibliotecario + ✍️ Escritor**
- **📚 Bibliotecario**: `nomic-embed-text` (100MB) para embeddings rápidos
- **✍️ Escritor**: `contador-oriental` (Gemma 2:2b) para respuestas
- **🗄️ Memoria**: PostgreSQL + pgvector para búsqueda semántica

### **🔄 Flujo Completo**
1. **Guardado** → Embedding + Vector en PostgreSQL
2. **Consulta** → Embedding rápido + búsqueda semántica  
3. **Respuesta** → Contexto relevante + Gemma 2:2b

---

## 📋 Fases de Implementación

### **Fase 1: Preparación de Infraestructura**

#### 1.1 Dependencias (UV)
```toml
# Agregar a pyproject.toml
dependencies = [
    # ... existentes ...
    "pgvector>=0.2.0",
    "asyncpg>=0.29.0",  # Async PostgreSQL driver
]
```

#### 1.2 UV Sync
```bash
# Actualizar dependencias
uv sync
# Generar uv.lock actualizado
```

#### 1.2 Extensión PostgreSQL
```bash
# Ejecutar en contenedor de BD
docker exec -it auditor_familiar_db psql -U postgres -d postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

#### 1.3 Modelo de Embeddings
```bash
# Descargar modelo especializado
ollama pull nomic-embed-text
```

---

### **Fase 2: Base de Datos - Migración 006**

#### 2.1 Crear Archivo de Migración
**Archivo**: `migrations/006_vector_memory.py`

```python
"""
Migración 006 - Memoria Vectorial del Contador
Habilita pgvector y crea la tabla para almacenamiento semántico.
Permite al Contador Oriental realizar búsquedas por contexto (RAG).

Integra con estructura existente:
- familias (id, nombre, email, activo)
- usuarios (id, familia_id, email, password_hash)
- family_members (id, familia_id, nombre, ...)
- incomes (id, familia_id, monto, fecha, ...)
- expenses (id, familia_id, monto, categoria, ...)
- monthly_expense_snapshots (id, familia_id, anio, mes, ...)
"""
from sqlalchemy import text
from configs.database_config import DatabaseConfig


def up(db) -> None:
    """Crear tabla de memoria vectorial con tipado estricto"""
    is_postgres: bool = DatabaseConfig.is_postgresql()

    if is_postgres:
        # 1. Habilitar la extensión vectorial
        db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        
        # 2. Crear tabla con soporte de vectores (768 para nomic-embed-text)
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_vector_memory (
                id           SERIAL PRIMARY KEY,
                familia_id   INTEGER NOT NULL REFERENCES familias(id),
                contenido    TEXT NOT NULL,
                embedding    VECTOR(768),
                metadata     JSONB,
                source_type  VARCHAR(50) NOT NULL, -- 'gasto', 'ingreso', 'snapshot', 'ocr'
                source_id    INTEGER, -- ID del registro original
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # 3. Índice HNSW optimizado para Orange Pi (RAM eficiente)
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_vector_memory_embedding 
            ON ai_vector_memory USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """))
        
        # 4. Índice por familia para multitenancy
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_vector_memory_familia 
            ON ai_vector_memory (familia_id)
        """))
        
        # 5. Índice compuesto para búsquedas eficientes
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_vector_memory_familia_source 
            ON ai_vector_memory (familia_id, source_type)
        """))
    else:
        # Fallback para SQLite (Desarrollo local)
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_vector_memory (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                familia_id   INTEGER NOT NULL,
                contenido    TEXT NOT NULL,
                embedding    TEXT, -- En SQLite guardamos el vector como string/json
                metadata     TEXT,
                source_type  TEXT NOT NULL,
                source_id    INTEGER,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

    print("✅ Tabla ai_vector_memory creada")
    if is_postgres:
        print("   - Extensión pgvector habilitada")
        print("   - Índice HNSW configurado para búsquedas rápidas")
        print("   - FK a familias(id) para integridad referencial")
        print("   - Índices optimizados para multitenancy")


def down(db) -> None:
    """Eliminar tabla de memoria vectorial"""
    db.execute(text("DROP TABLE IF EXISTS ai_vector_memory"))
    print("↩️ Tabla ai_vector_memory eliminada")
```

---

### **Fase 3: Modelos de Datos**

#### 3.1 Modelo de Memoria (Tipado Estricto)
**Archivo**: `models/memoria_model.py`

```python
from __future__ import annotations

from typing import Optional, Dict, Any
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Text, JSONB, Integer, String, TIMESTAMP
from database.base import Base


class MemoriaContable(Base):
    """Modelo de memoria vectorial con tipado estricto"""
    __tablename__ = "ai_vector_memory"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    familia_id: Mapped[int] = mapped_column(Integer, nullable=False)
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    # nomic-embed-text usa 768 dimensiones
    embedding: Mapped[list[float]] = mapped_column(Vector(768))
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'gasto', 'ingreso', 'snapshot', 'ocr'
    source_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[str] = mapped_column(TIMESTAMP, default="CURRENT_TIMESTAMP")
    updated_at: Mapped[str] = mapped_column(TIMESTAMP, default="CURRENT_TIMESTAMP")
    
    def __repr__(self) -> str:
        return f"MemoriaContable(id={self.id}, familia_id={self.familia_id}, source_type={self.source_type})"
```

---

### **Fase 4: Repositorio de Memoria**

#### 4.1 MemoriaRepository (Async + Tipado Estricto)
**Archivo**: `repositories/memoria_repository.py`

```python
from __future__ import annotations

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from repositories.base_table_repository import BaseTableRepository
from models.memoria_model import MemoriaContable


class MemoriaRepository(BaseTableRepository[MemoriaContable]):
    """Repository de memoria vectorial con async y tipado estricto"""
    
    def __init__(self, session: AsyncSession, familia_id: Optional[int] = None) -> None:
        super().__init__(session, MemoriaContable, familia_id)
    
    async def buscar_similares(
        self, 
        embedding_consulta: List[float], 
        limit: int = 3
    ) -> List[MemoriaContable]:
        """Buscar registros semánticamente similares usando cosine distance"""
        query = (
            select(MemoriaContable)
            .where(MemoriaContable.familia_id == self.familia_id)
            .order_by(MemoriaContable.embedding.cosine_distance(embedding_consulta))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def buscar_por_familia(
        self, 
        limit: int = 10,
        source_type: Optional[str] = None
    ) -> List[MemoriaContable]:
        """Obtener recuerdos recientes de la familia con filtros opcionales"""
        query = select(MemoriaContable).where(MemoriaContable.familia_id == self.familia_id)
        
        if source_type:
            query = query.where(MemoriaContable.source_type == source_type)
        
        query = query.order_by(MemoriaContable.created_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def buscar_por_source(
        self, 
        source_type: str, 
        source_id: int
    ) -> Optional[MemoriaContable]:
        """Buscar memoria por source_type y source_id"""
        query = select(MemoriaContable).where(
            MemoriaContable.familia_id == self.familia_id,
            MemoriaContable.source_type == source_type,
            MemoriaContable.source_id == source_id
        )
        result = await self.session.execute(query)
        return result.scalars().first()
```

---

### **Fase 5: Servicios de IA**

#### 5.1 Servicio de Embeddings
**Archivo**: `services/embedding_service.py`

```python
import httpx
from result import Ok, Err, Result

class EmbeddingService:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
    
    async def generar_embedding(self, texto: str) -> Result[list[float], str]:
        """Generar embedding usando nomic-embed-text"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ollama_url}/api/embeddings",
                    json={"model": "nomic-embed-text", "prompt": texto}
                )
                response.raise_for_status()
                return Ok(response.json()["embedding"])
        except Exception as e:
            return Err(f"Error al generar embedding: {str(e)}")
```

#### 5.2 Servicio de Memoria IA
**Archivo**: `services/ia_memory_service.py`

```python
from result import Ok, Err
from services.embedding_service import EmbeddingService
from repositories.memoria_repository import MemoriaRepository
from models.memoria_model import MemoriaContable

class IAMemoryService:
    def __init__(self, memoria_repo: MemoriaRepository, embedding_service: EmbeddingService):
        self.repo = memoria_repo
        self.embedding_service = embedding_service
    
    async def registrar_evento_contable(
        self, 
        familia_id: int, 
        texto_plano: str, 
        metadata: dict
    ) -> Result[MemoriaContable, str]:
        """Registrar un evento contable en la memoria vectorial"""
        
        # 1. Generar embedding
        embedding_result = await self.embedding_service.generar_embedding(texto_plano)
        
        if isinstance(embedding_result, Err):
            return Err(f"Error generando embedding: {embedding_result.value}")
        
        # 2. Crear registro de memoria
        nueva_memoria = MemoriaContable(
            familia_id=familia_id,
            contenido=texto_plano,
            embedding=embedding_result.value,
            metadata_json=metadata
        )
        
        # 3. Guardar en base de datos
        try:
            resultado = self.repo.create(nueva_memoria)
            return Ok(resultado)
        except Exception as e:
            return Err(f"Error guardando memoria: {str(e)}")
    
    async def buscar_contexto_para_pregunta(
        self, 
        familia_id: int, 
        pregunta: str, 
        limit: int = 5
    ) -> Result[list[str], str]:
        """Buscar contexto relevante para una pregunta con validación de longitud"""
        
        # 1. Generar embedding de la pregunta
        embedding_result = await self.embedding_service.generar_embedding(pregunta)
        
        if isinstance(embedding_result, Err):
            return Err(f"Error generando embedding de pregunta: {embedding_result.value}")
        
        # 2. Buscar registros similares
        self.repo.familia_id = familia_id
        recuerdos_similares = self.repo.buscar_similares(embedding_result.value, limit)
        
        # 3. Extraer contenido y validar longitud para Gemma 2:2b (4096 tokens)
        contextos = [recuerdo.contenido for recuerdo in recuerdos_similares]
        
        # 4. Validar longitud total (~4 chars por token, margen de seguridad)
        longitud_total = sum(len(ctx) for ctx in contextos)
        max_longitud = 15000  # ~3750 tokens con margen de seguridad
        
        if longitud_total > max_longitud:
            # Reducir contexto si excede límite de Gemma
            contextos_reducidos = []
            longitud_actual = 0
            
            for ctx in contextos:
                if longitud_actual + len(ctx) > max_longitud:
                    break
                contextos_reducidos.append(ctx)
                longitud_actual += len(ctx)
            
            contextos = contextos_reducidos
        
        return Ok(contextos)
```

---

### **Fase 5.5: Patrón Observer (Eventos Contables)**

#### 5.5.1 Sistema de Eventos
**Archivo**: `core/events.py`

```python
from __future__ import annotations

from typing import Protocol, List, Any, Dict
from dataclasses import dataclass
from enum import Enum
import asyncio
from result import Ok, Err


class EventType(Enum):
    GASTO_CREADO = "gasto_creado"
    INGRESO_CREADO = "ingreso_creado"
    SNAPSHOT_CREADO = "snapshot_creado"
    OCR_PROCESADO = "ocr_procesado"


@dataclass
class Event:
    """Evento del sistema con tipado estricto"""
    type: EventType
    familia_id: int
    data: Dict[str, Any]
    source_id: Optional[int] = None
    timestamp: Optional[str] = None


class EventHandler(Protocol):
    """Protocolo para handlers de eventos"""
    async def handle(self, event: Event) -> None:
        ...


class EventSystem:
    """Sistema de eventos con async y tipado estricto"""
    
    def __init__(self) -> None:
        self._handlers: Dict[EventType, List[EventHandler]] = {}
    
    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Suscribir handler a tipo de evento"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    async def publish(self, event: Event) -> None:
        """Publicar evento a todos los handlers suscriptos"""
        handlers = self._handlers.get(event.type, [])
        
        # Ejecutar handlers en paralelo sin bloquear
        tasks = [
            asyncio.create_task(handler.handle(event))
            for handler in handlers
        ]
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def clear(self) -> None:
        """Limpiar todos los handlers"""
        self._handlers.clear()


# Singleton global para el sistema de eventos
event_system = EventSystem()
```

#### 5.5.2 Handler de Memoria IA
**Archivo**: `services/memory_event_handler.py`

```python
from __future__ import annotations

from typing import Dict, Any
from core.events import EventHandler, Event, EventType
from services.ia_memory_service import IAMemoryService


class MemoryEventHandler(EventHandler):
    """Handler para registrar eventos en memoria IA"""
    
    def __init__(self, memory_service: IAMemoryService) -> None:
        self.memory_service = memory_service
    
    async def handle(self, event: Event) -> None:
        """Manejar evento y registrar en memoria vectorial"""
        try:
            # Construir texto para embedding según tipo de evento
            if event.type == EventType.GASTO_CREADO:
                texto = self._formatear_gasto(event.data)
            elif event.type == EventType.INGRESO_CREADO:
                texto = self._formatear_ingreso(event.data)
            elif event.type == EventType.SNAPSHOT_CREADO:
                texto = self._formatear_snapshot(event.data)
            elif event.type == EventType.OCR_PROCESADO:
                texto = self._formatear_ocr(event.data)
            else:
                return
            
            # Registrar en memoria (async, no bloquea)
            await self.memory_service.registrar_evento_contable(
                familia_id=event.familia_id,
                texto_plano=texto,
                metadata={
                    "event_type": event.type.value,
                    "source_id": event.source_id,
                    **event.data
                }
            )
            
        except Exception as e:
            # Log error pero no rompa el flujo principal
            print(f"Error en MemoryEventHandler: {e}")
    
    def _formatear_gasto(self, data: Dict[str, Any]) -> str:
        """Formatear datos de gasto para embedding"""
        return (
            f"Gasto registrado: {data.get('descripcion', '')} "
            f"por ${data.get('monto', 0)} en categoría {data.get('categoria', '')}. "
            f"Método: {data.get('metodo_pago', '')}. "
            f"Fecha: {data.get('fecha', '')}."
        )
    
    def _formatear_ingreso(self, data: Dict[str, Any]) -> str:
        """Formatear datos de ingreso para embedding"""
        return (
            f"Ingreso registrado: {data.get('descripcion', '')} "
            f"por ${data.get('monto', 0)} en categoría {data.get('categoria', '')}. "
            f"Miembro: {data.get('miembro', '')}. "
            f"Fecha: {data.get('fecha', '')}."
        )
    
    def _formatear_snapshot(self, data: Dict[str, Any]) -> str:
        """Formatear datos de snapshot para embedding"""
        return (
            f"Snapshot mensual: {data.get('categoria', '')} "
            f"total ${data.get('total_dinero', 0)} "
            f"en {data.get('cantidad_compras', 0)} compras. "
            f"Ticket promedio: ${data.get('ticket_promedio', 0)}. "
            f"Período: {data.get('mes', '')}/{data.get('anio', '')}."
        )
    
    def _formatear_ocr(self, data: Dict[str, Any]) -> str:
        """Formatear datos de OCR para embedding"""
        return (
            f"Ticket procesado por OCR: {data.get('texto_extraido', '')}. "
            f"Total estimado: ${data.get('total_estimado', 0)}. "
            f"Comercio: {data.get('comercio', '')}. "
            f"Fecha: {data.get('fecha', '')}."
        )
```

---

### **Fase 6: Integración con Controllers (Observer Pattern)**

#### 6.1 Modificar GastoController (Publicar Eventos)
**Archivo**: `controllers/gasto_controller.py`

```python
from __future__ import annotations

from typing import Optional
from result import Ok, Err
from core.events import event_system, Event, EventType
from controllers.base_controller import BaseController


class GastoController(BaseController):
    """Controller de gastos con Observer Pattern y async"""
    
    def __init__(self, familia_id: int) -> None:
        super().__init__(familia_id)
    
    async def crear_gasto(self, gasto_data) -> Ok:
        """Crear gasto y publicar evento (non-blocking)"""
        
        # 1. Lógica normal de guardar gasto
        result = await self.gasto_service.save(gasto_data)
        
        if isinstance(result, Ok):
            # 2. Publicar evento (async, no bloquea la UI)
            gasto = result.value
            
            event = Event(
                type=EventType.GASTO_CREADO,
                familia_id=gasto.familia_id,
                source_id=gasto.id,
                data={
                    "descripcion": gasto.descripcion,
                    "monto": float(gasto.monto),
                    "categoria": gasto.categoria,
                    "metodo_pago": gasto.metodo_pago,
                    "fecha": str(gasto.fecha),
                    "recurrente": gasto.es_recurrente
                }
            )
            
            # Publicar sin await (fire-and-forget seguro)
            import asyncio
            import logging
            
            # Wrapper con logging y retry para Orange Pi
            async def safe_publish():
                try:
                    await event_system.publish(event)
                except Exception as e:
                    # Log específico para fallos de embedding en Orange Pi
                    logging.error(
                        f"[MEMORY_EVENT_FAILED] familia_id={gasto.familia_id} "
                        f"event_type={event.type.value} error={str(e)}"
                    )
            
            asyncio.create_task(safe_publish())
        
        return result
```

#### 6.2 Modificar AIController
**Archivo**: `controllers/ai_controller.py`

```python
from services.ia_memory_service import IAMemoryService

class AIController(BaseController):
    def __init__(self, familia_id: int, memory_service: IAMemoryService):
        super().__init__(familia_id)
        self.memory_service = memory_service
    
    async def consultar_con_memoria(self, pregunta: str) -> Result[str, str]:
        """Consulta al Contador Oriental con memoria contextual"""
        
        # 1. Buscar contexto relevante
        contexto_result = await self.memory_service.buscar_contexto_para_pregunta(
            familia_id=self.familia_id,
            pregunta=pregunta,
            limit=5
        )
        
        # 2. Construir prompt con contexto
        if isinstance(contexto_result, Ok) and contexto_result.value:
            contexto_previo = "\n".join([f"- {ctx}" for ctx in contexto_result.value])
            prompt_enriquecido = f"""
DATOS CONTABLES RECUPERADOS:
{contexto_previo}

PREGUNTA DEL USUARIO:
{pregunta}

Responde basándote en los datos proporcionados. Si no hay datos relevantes, indícalo claramente.
"""
        else:
            prompt_enriquecido = pregunta
        
        # 3. Llamar al servicio de IA existente
        return await self.ai_service.consultar(prompt_enriquecido)
```

---

### **Fase 7: Actualización de Vistas**

#### 7.1 Modificar AIAdvisorView
**Archivo**: `views/pages/ai_advisor_view.py`

```python
# En el método de consulta
async def _on_consultar(self, e):
    pregunta = self.input_field.value
    
    # Usar el nuevo controller con memoria
    controller = AIController(
        familia_id=self.familia_id,
        memory_service=self.memory_service
    )
    
    result = await controller.consultar_con_memoria(pregunta)
    
    if isinstance(result, Ok):
        self._add_message("user", pregunta)
        self._add_message("assistant", result.value)
    else:
        self._add_message("assistant", f"Error: {result.value}")
```

---

### **Fase 8: Testing**

#### 8.1 Tests de Memoria
**Archivo**: `tests/test_memoria_service.py`

```python
import pytest
from unittest.mock import AsyncMock, Mock
from services.ia_memory_service import IAMemoryService
from repositories.memoria_repository import MemoriaRepository
from services.embedding_service import EmbeddingService

@pytest.fixture
def mock_embedding_service():
    service = Mock(spec=EmbeddingService)
    service.generar_embedding = AsyncMock(return_value=Ok([0.1, 0.2, 0.3] * 256))  # 768 dimensiones
    return service

@pytest.fixture
def mock_memoria_repo():
    repo = Mock(spec=MemoriaRepository)
    repo.create = Mock(return_value=Mock(id=1, contenido="test"))
    repo.buscar_similares = Mock(return_value=[])
    return repo

@pytest.mark.asyncio
async def test_registrar_evento_contable(mock_embedding_service, mock_memoria_repo):
    service = IAMemoryService(mock_memoria_repo, mock_embedding_service)
    
    result = await service.registrar_evento_contable(
        familia_id=1,
        texto_plano="Gasto de $1000 en supermercado",
        metadata={"categoria": "alimentos"}
    )
    
    assert isinstance(result, Ok)
    mock_embedding_service.generar_embedding.assert_called_once()
    mock_memoria_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_buscar_contexto_para_pregunta(mock_embedding_service, mock_memoria_repo):
    service = IAMemoryService(mock_memoria_repo, mock_embedding_service)
    
    # Configurar mocks
    mock_memoria_repo.buscar_similares.return_value = [
        Mock(contenido="Gasto en supermercado"),
        Mock(contenido="Gasto en carnicería")
    ]
    
    result = await service.buscar_contexto_para_pregunta(
        familia_id=1,
        pregunta="¿En qué gasté más en alimentos?"
    )
    
    assert isinstance(result, Ok)
    assert len(result.value) == 2
```

---

### **Fase 9: Configuración y Deploy**

#### 9.1 Actualizar Docker Compose
**Archivo**: `docker-compose.yml`

```yaml
services:
  app:
    # ... existente ...
    environment:
      # ... existente ...
      # Agregar soporte para embeddings
      OLLAMA_EMBEDDING_MODEL: nomic-embed-text
      MEMORY_SERVICE_ENABLED: "true"
```

#### 9.2 Actualizar Configuración
**Archivo**: `configs/app_config.py`

```python
class AppConfig:
    # ... existente ...
    
    # Configuración de memoria IA
    OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
    MEMORY_SERVICE_ENABLED = os.getenv("MEMORY_SERVICE_ENABLED", "true").lower() == "true"
```

---

## 🚀 Plan de Ejecución

### **Paso 1: Preparación (1 hora)**
1. Agregar `pgvector` a `pyproject.toml`
2. Descargar `nomic-embed-text` en Ollama
3. Habilitar extensión `vector` en PostgreSQL

### **Paso 2: Base de Datos (30 minutos)**
1. Crear migración `006_vector_memory.py`
2. Ejecutar migración: `uv run python migrations/migrate.py migrate`
3. Verificar tabla creada

### **Paso 3: Modelo y Repository (1 hora)**
1. Crear `models/memoria_model.py`
2. Crear `repositories/memoria_repository.py`
3. Tests básicos del repository

### **Paso 4: Servicios de IA (2 horas)**
1. Crear `services/embedding_service.py`
2. Crear `services/ia_memory_service.py`
3. Tests completos de servicios

### **Paso 5: Integración Controllers (1.5 horas)**
1. Modificar `GastoController` para registrar memoria
2. Modificar `AIController` para usar memoria
3. Tests de integración

### **Paso 6: Actualización UI (1 hora)**
1. Modificar `AIAdvisorView` para usar nueva funcionalidad
2. Testing de UI con mocks

### **Paso 7: Testing Final (1 hora)**
1. Tests end-to-end
2. Performance testing en Orange Pi
3. Validación de multitenancy

---

## 🎯 Beneficios Esperados

### **⚡ Performance**
- **Búsquedas milisegundos** con índice HNSW
- **RAM optimizada** — Solo contexto relevante
- **Asíncrono** — UI no bloqueada

### **🧠 Inteligencia**
- **Búsqueda semántica** — Entiende "plata", "guita", "boletas"
- **Contexto relevante** — Respuestas basadas en datos reales
- **Aprendizaje continuo** — Cada transacción enriquece la memoria

### **🛡️ Escalabilidad**
- **Multitenancy** — `familia_id` aísla datos
- **Millones de registros** — PostgreSQL maneja volumen
- **OCR futuro** — Flujo idéntico para tickets

---

## 🔧 Consideraciones Técnicas

### **Orange Pi 5 Plus Optimización (Mejoras de Trinchera)**
- **Índice HNSW optimizado** — `WITH (m = 16, ef_construction = 64)` para RAM eficiente
- **nomic-embed-text** — 100MB vs modelos pesados
- **Tareas asíncronas** — No bloquear UI Flet
- **Fire-and-Forget seguro** — Logging específico para fallos de embedding
- **Context Window validado** — Máximo 15000 chars (~3750 tokens) para Gemma 2:2b
- **Logging estructurado** — `[MEMORY_EVENT_FAILED] familia_id=X event_type=Y error=Z`

### **Seguridad y Privacidad**
- **Aislamiento por familia** — `familia_id` obligatorio
- **Datos encriptados** — PostgreSQL con SSL
- **Sin datos sensibles** — Solo texto procesado

### **Calidad de Datos**
- **Limpieza de texto** — Antes de generar embeddings
- **Metadata estructurada** — JSONB para filtros
- **Validación de entrada** — Prevenir garbage in/garbage out

---

## 📊 Métricas de Éxito

### **Técnicas**
- **< 100ms** para búsqueda semántica
- **< 500ms** para respuesta completa
- **> 95%** uptime del servicio

### **Funcionales**
- **Respuestas contextuales** — Basadas en datos reales
- **Búsquedas naturales** — "¿En qué se me fue la plata?"
- **Memoria persistente** — Aprendizaje continuo

---

## 🎉 Resultado Final

El Contador Oriental tendrá:

1. **Memoria permanente** de todas las transacciones
2. **Búsquedas inteligentes** por contexto semántico
3. **Respuestas precisas** basadas en datos reales
4. **Performance óptima** en Orange Pi 5 Plus
5. **Escalabilidad** para OCR y futuras features

**🇺🇾 El contador uruguayo más inteligente del mercado!**
