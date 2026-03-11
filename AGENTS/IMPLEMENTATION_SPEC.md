# IMPLEMENTATION_SPEC.md - Contador Oriental

## OCR Ticket Upload Flow

### Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Flet App   │────▶│  OCR API    │────▶│ PostgreSQL  │
│  (port 8550)│     │(port 8551)  │     │ (port 5432)│
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                    │
       │  1. session_id    │                    │
       │◀───────────────── │                    │
       │                   │                    │
       │  2. QR/URL        │                    │
       │─── to user ──────▶│                    │
       │                   │                    │
       │                   │  3. Upload form     │
       │                   │◀─── user ─────────│
       │                   │                    │
       │                   │  4. Process OCR    │
       │                   │───▶ Tesseract      │
       │                   │───▶ Gemma2        │
       │                   │                    │
       │                   │  5. Save result    │
       │                   │──────────────────▶│
       │                   │                    │
       │  6. Poll result  │                    │
       │◀─────────────────│                    │
       │                   │                    │
```

### States (ticket_upload_view.py)

| State | Description |
|-------|-------------|
| IDLE | Initial state, show QR/URL for upload |
| LOADING | Polling for OCR result |
| CONFIRM | OCR result ready, user confirms |
| ERROR | Error occurred |

### Key Methods

| Method | File | Description |
|--------|------|-------------|
| `_preparar_sesion()` | ticket_upload_view.py | Generate UUID session_id |
| `_generar_qr_code()` | ticket_upload_view.py | Generate QR display |
| `_iniciar_polling()` | ticket_upload_view.py | Start polling loop |
| `_esperar_resultado()` | ticket_upload_view.py | Poll every 2s, max 120s |

### OCR API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/upload-form?session_id=xxx` | HTML form with camera input |
| POST | `/upload-form-submit` | Process uploaded image |
| GET | `/resultado/{session_id}` | Poll result (consumes session) |

### Response Format

```python
{
    "success": True,
    "ready": True,
    "monto": 1250.0,
    "fecha": "2026-03-04",
    "comercio": "Tienda Inglesa",
    "items": ["leche", "pan"],
    "confianza_ocr": 0.85,
    "texto_crudo": "..."
}
```

### Environment Variables

```python
_OCR_INTERNAL = os.getenv("OCR_API_URL", "http://ocr_api:8551")
_OCR_PUBLIC = os.getenv("OCR_API_PUBLIC_URL", "http://localhost:8551")
```

## AI Advisor (Contador Virtual)

### Architecture

```
User Query → AI Controller → AI Service → Ollama API
                │              │
                │         Vector Memory
                │         (pgvector)
                │
                ▼
         RAG Context
         (knowledge/)
```

### Components

| Component | File | Purpose |
|-----------|------|---------|
| AIController | ai_controller.py | UI handling |
| AIAdvisorService | ai_advisor_service.py | Main AI logic |
| EmbeddingService | embedding_service.py | Text embeddings |
| IAMemoryService | ia_memory_service.py | Vector storage |

### Models Used

| Model | Purpose |
|-------|---------|
| `gemma2:2b` | Chat responses |
| `nomic-embed-text` | Embeddings (768 dimensions) |

### RAG Context

- Knowledge files in `knowledge/` directory
- Vector memory stored in `ai_vector_memory` table
- Searches similar context based on user query

## Database Tables

### ocr_sessions

```python
class OCRSession(Base):
    __tablename__ = "ocr_sessions"
    session_id: Mapped[str]      # PK
    familia_id: Mapped[int]
    resultado_json: Mapped[str | None]
    created_at: Mapped[datetime]
    expires_at: Mapped[datetime]  # TTL: created_at + 10 min
```

### ai_vector_memory

```python
class AIVectorMemory(Base):
    __tablename__ = "ai_vector_memory"
    id: Mapped[int]              # PK
    familia_id: Mapped[int]
    contenido: Mapped[str]
    embedding: Mapped[list[float]]  # 768 dimensions
    created_at: Mapped[datetime]
```

## Event System

### Event Types

```python
class EventType(Enum):
    GASTO_CREADO = "gasto_creado"
    GASTO_ACTUALIZADO = "gasto_actualizado"
    GASTO_ELIMINADO = "gasto_eliminado"
    INGRESO_CREADO = "ingreso_creado"
```

### Usage

```python
from core.events import Event, EventType, event_system

event = Event(
    type=EventType.GASTO_CREADO,
    familia_id=self._familia_id,
    source_id=expense.id,
    data={...},
)
event_system.fire_and_forget(event)
```

## Docker Configuration

### Services

```yaml
services:
  app:
    build: .
    ports:
      - "8550:8550"
    environment:
      - DATABASE_URL=postgresql://...
      - OCR_API_URL=http://ocr_api:8551

  ocr_api:
    build: ./ocr_api
    ports:
      - "8551:8551"
    environment:
      - DATABASE_URL=postgresql://...

  postgres:
    image: pgvector/pgvector:pg16
    ports:
      - "5432:5432"
```

## Fleting CLI Commands

```bash
# Create new page (model + controller + view)
uv run fleting create page <name>

# Create new components
uv run fleting create view <name>
uv run fleting create model <name>
uv run fleting create controller <name>

# Database
uv run fleting db migrate
uv run fleting db seed
uv run fleting db make <name>
```

## Known Limitations

1. **FilePicker in web mode**: Doesn't work in Docker. Use OCR microservice pattern.
2. **QR code images**: Generated QR may not display correctly in Flet web. Use URL display fallback.
3. **launch_url in web mode**: Doesn't work. Use `ft.Url` with `target=ft.UrlTarget.BLANK`.

## Diagnostic Tools

```bash
# Check Flet API compatibility
uv run python check_flet.py --compat
uv run python check_flet.py Card
```
