# AGENTS.md - Contador Oriental

This file provides guidance for AI agents operating in this codebase.

---

## 1. Build / Lint / Test Commands

### Prerequisites
- **Python**: 3.12+
- **Package Manager**: `uv` (required)
- **Database**: PostgreSQL with pgvector extension
- **Docker**: For running PostgreSQL and OCR service

### Development Setup
```bash
# Install dependencies
uv sync

# Start PostgreSQL (via Docker)
docker compose up -d postgres

# Run migrations
uv run fleting db migrate

# Seed data (development only)
$env:OLLAMA_BASE_URL="http://localhost:11434"
uv run fleting db seed
```

### Running Tests

```bash
# Run all tests
uv run pytest -v

# Run a single test file
uv run pytest tests/test_memoria_service.py -v

# Run a specific test
uv run pytest tests/test_expense_service.py::TestExpenseService::test_create_expense_success -v

# Run with coverage
uv run pytest --cov=. --cov-report=html

# Run only tests that don't require database (memory service tests use mocks)
uv run pytest tests/test_memoria_service.py -v
```

### Database Migrations
```bash
# Check migration status
uv run fleting db status

# Apply pending migrations
uv run fleting db migrate

# Create new migration
uv run fleting db make <migration_name>

# Rollback last migration
uv run fleting db rollback
```

### Fleting CLI Commands
This project uses **Fleting** - a Flet framework for building production-ready Flet applications with MVC architecture.

```bash
# Project Commands
uv run fleting init <app_name>       # Initialize a new Fleting project
uv run fleting info                  # Show version and system information
uv run fleting run                  # Run the application

# Create Commands
uv run fleting create page <name>    # Create a page (model + controller + view)
uv run fleting create view <name>   # Create a new view
uv run fleting create model <name>  # Create a new model
uv run fleting create controller <name>  # Create a new controller

# Delete Commands
uv run fleting delete page <name>   # Delete an existing page
uv run fleting delete view <name>   # Delete a view
uv run fleting delete model <name>  # Delete a model
uv run fleting delete controller <name>  # Delete a controller

# List Commands
uv run fleting list pages           # List all pages
uv run fleting list controllers     # List all controllers
uv run fleting list views          # List all views
uv run fleting list models         # List all models
uv run fleting list routes         # List all routes

# Database Commands
uv run fleting db init              # Initialize the database
uv run fleting db migrate          # Run database migrations
uv run fleting db seed             # Seed the database with initial data
uv run fleting db make <name>      # Create a new migration
uv run fleting db rollback         # Rollback the last migration
uv run fleting db status           # Show current database migration status
uv run fleting db model pull       # Generate models from the database schema
uv run fleting db model pull <table>  # Generate model for a specific table

# Console
uv run fleting shell               # Open interactive database shell (SQLite only)
```

### Linting & Type Checking
```bash
# Lint with ruff
uv run ruff check .

# Format code
uv run ruff format .

# Type check with ty (faster alternative to mypy)
uv run ty check .
```

---

## 2. Code Style Guidelines

### General Principles
- **Python 3.12+** with strict type hints
- Use `from __future__ import annotations` for postponed evaluation
- **Line length**: 88 characters (ruff default)
- **Indentation**: 4 spaces
- **Quotes**: Double quotes (`"`)
- **No comments** unless explicitly requested

### Project Architecture

```
├── controllers/     # Flet UI controllers + business logic
├── services/        # Business logic layer (no DB access)
├── repositories/    # Data access layer (DB queries)
├── models/          # Pydantic models, SQLAlchemy tables, errors
├── views/           # Flet UI pages
├── core/            # Event system, routing, session management
├── database/        # SQLAlchemy engine + tables
├── constants/       # Enums, messages, config
├── tests/           # pytest fixtures + test cases
├── migrations/      # fleting migrations
├── knowledge/       # RAG context files (Uruguayan tax law)
└── ocr_api/        # FastAPI microservice for ticket OCR
```

### Naming Conventions
- **Classes**: `PascalCase` (e.g., `ExpenseController`, `AppError`)
- **Functions/Variables**: `snake_case` (e.g., `add_expense`, `familia_id`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRY_COUNT`)
- **Files**: `snake_case.py` (e.g., `expense_controller.py`)

### Imports Order (ruff)
1. Standard library (`from __future__ import annotations` first)
2. Third-party packages
3. Local application imports

```python
from __future__ import annotations

import logging
from datetime import date
from collections.abc import Generator

from result import Ok, Err

from controllers.base_controller import BaseController
from models.expense_model import Expense
from services.expense_service import ExpenseService
```

### Type Hints
- Use **strict type hints** everywhere
- Use union syntax (`X | None`) instead of `Optional[X]`
- Use `list[X]`, `dict[K, V]` instead of `List`, `Dict`
- Add return types to all functions: `def foo() -> str:`

```python
def add_expense(self, expense: Expense) -> Result[Expense, AppError]:
    ...

def list_expenses(self) -> list[Expense]:
    ...

def get_summary_by_categories(
    self,
    year: int | None = None,
    month: int | None = None,
) -> dict[str, float]:
    ...
```

### Error Handling
- **Use `Result[T, E]`** from the `result` library (not exceptions)
- Never raise exceptions in services/repositories
- Return `Result[SuccessType, AppError]` or `Result[None, AppError]`

```python
from result import Ok, Err

from models.errors import AppError, DatabaseError, ValidationError

def create_expense(
    self, expense: Expense
) -> Result[Expense, ValidationError | DatabaseError]:
    for check in (validate_monto_positive(expense.monto), ...):
        if check.is_err():
            return check
    return self._repo.add(expense)
```

- Define custom errors in `models/errors.py`:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class AppError:
    message: str

@dataclass(frozen=True)
class DatabaseError(AppError):
    pass

@dataclass(frozen=True)
class ValidationError(AppError):
    pass
```

### Database Layer
- Use **SQLAlchemy** with `BaseTableRepository(ABC, Generic)`
- Controllers use context manager pattern for sessions:

```python
class ExpenseController(BaseController):
    def add_expense(self, expense: Expense) -> Result[Expense, AppError]:
        with self._get_session() as session:
            repo = ExpenseRepository(session, self._familia_id)
            service = ExpenseService(repo)
            return service.create_expense(expense)
```

- Repositories must filter by `familia_id` for multi-tenancy

### Pydantic Models
- Use Pydantic for all input/output validation
- Use `frozen=True` for immutable models
- Use enums for categories

```python
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field

class ExpenseCategory(Enum):
    ALMACEN = "Almacén"
    HOGAR = "Hogar"
    ...

class Expense(BaseModel):
    monto: float = Field(gt=0)
    descripcion: str = Field(min_length=1)
    fecha: date
    categoria: ExpenseCategory
    es_recurrente: bool = False
```

### Testing Guidelines
- Tests use **real PostgreSQL** with transaction rollback for isolation
- Use fixtures from `tests/conftest.py`
- Mock external services (Ollama) for unit tests

```python
class TestExpenseService:
    @pytest.fixture
    def service(self, db_session):
        from repositories.expense_repository import ExpenseRepository
        repo = ExpenseRepository(db_session, familia_id=1)
        return ExpenseService(repo)

    def test_create_expense_success(self, service, sample_expense_data):
        expense = Expense(**sample_expense_data)
        result = service.create_expense(expense)
        assert isinstance(result, Ok)
```

### UI / Flet
- Flet views go in `views/pages/`
- Controllers handle business logic, views handle rendering
- Use `page.launch_url()` for external links (note: doesn't work in web mode)
- For file upload in web mode, use the OCR microservice pattern

### Microservice Inter-connectivity
- **Internal Network**: Containers communicate via Docker internal DNS.
- **Flet to OCR**: `app` calls `http://auditor_familiar_ocr_api:8551`.
- **OCR to Database**: `ocr_api` writes directly to the shared PostgreSQL instance.
- **Data Sharing**: The OCR service writes the parsed JSON to a temporary results table or a shared Redis/Cache. `app` polls this state using the `session_id`.

### Manual Upload Protocol (The app4 <-> app5 Bridge)
When implementing or modifying ticket upload features:

**Flow Overview (Opción A — polling automático, implementado 2026-03-05):**
```
1. IDLE     → Vista carga → genera session_id (UUID) → arranca polling inmediatamente
2. IDLE     → Muestra botón "Abrir formulario en nueva pestaña"
3. LOADING  → Polling activo: GET /resultado/{session_id} cada 2s (hasta 120s)
4. External → Usuario abre formulario, sube foto → OCR procesa
5. CONFIRM  → Resultado detectado → UI avanza sola (sin botón manual)
6. CONFIRM  → Usuario revisa/edita datos y confirma → gasto guardado
```

**IMPORTANTE**: No hay botón "Ya subí la foto" — la pantalla avanza automáticamente.

**Implementation Details:**

| State | File | Key Methods |
|-------|------|-------------|
| IDLE | `views/pages/ticket_upload_view.py` | `_preparar_sesion()`, `_build_idle()` |
| LOADING/POLLING | `views/pages/ticket_upload_view.py` | `_iniciar_polling()`, `_esperar_resultado()` |
| CONFIRM | `views/pages/ticket_upload_view.py` | `_build_confirm()`, `_on_confirmar()` |

**Polling Configuration:**
- **Interval**: 2 seconds between requests
- **Max wait**: 120 seconds (2 minutes)
- **Endpoint**: `GET {OCR_INTERNAL}/resultado/{session_id}`
- **Response**: `{"ready": True/False, "success": True/False, "monto": ..., "fecha": ..., "comercio": ..., ...}`

**Important:** After receiving the result, the session is consumed (popped from memory). The user must complete the flow in one session.

**URL Environment Variables:**
```python
_OCR_INTERNAL = os.getenv("OCR_API_URL", "http://ocr_api:8551")  # Flet → OCR
_OCR_PUBLIC = os.getenv("OCR_API_PUBLIC_URL", "http://localhost:8551")  # User browser → OCR
```

### OCR Service API Endpoints

**ocr_api/main.py** - FastAPI microservice:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/upload-form?session_id=xxx&familia_id=1` | HTML form with camera input |
| POST | `/upload-form-submit` | Process uploaded image |
| GET | `/resultado/{session_id}` | Poll for OCR result (consumes session) |

**Data Flow in OCR API:**
1. `/upload-form-submit` receives image → saves to temp file
2. Tesseract extracts raw text + confidence score
3. Gemma2 parses JSON: `{monto, fecha, comercio, items}`
4. Result stored in `_resultados[session_id]` (in-memory dict)
5. Image file deleted immediately after processing

**Response Format:**
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

### OCR Service Constraints (ocr_api)
- **Zero Flet dependency**: This service must not import `flet`. It is a pure FastAPI + Jinja2 app.
- **HTML/JS Standards**: Use standard HTML5 `<input capture="environment">` to ensure mobile camera compatibility.
- **Privacy**: Process images in memory or delete local copies immediately after Tesseract/Gemma analysis.

### Key Libraries
| Library | Purpose |
|---------|---------|
| `flet` | UI framework |
| `sqlalchemy` | ORM |
| `pydantic` | Data validation |
| `result` | Error handling |
| `ruff` | Linting/formatting |
| `ty` | Type checking |
| `pytest` | Testing |
| `pgvector` | Vector similarity search |
| `qrcode` | QR code generation for ticket upload |
| `pillow` | Image processing for OCR |
| `pytesseract` | OCR text extraction |

### Ticket Upload UX Improvements
- **QR Code**: Automatically generated QR code for easy scanning from mobile
- **Step-by-step instructions**: Clear "How it works" card with numbered steps
- **Better visual hierarchy**: Icons, cards, and colors guide the user
- **Mobile-first**: QR code makes it easy to transfer to phone for photo capture

**Current Implementation (`views/pages/ticket_upload_view.py`):**

| Component | Method | Description |
|-----------|--------|-------------|
| QR Generator | `_generar_qr_code(url)` | Generates QR code from form URL using `qrcode` library |
| Idle State | `_build_idle()` | Main UI with QR, instructions, and action buttons |
| States | `_Estado` enum | IDLE, LOADING, CONFIRM, ERROR |

**Code Example - QR Generation:**
```python
import qrcode

def _generar_qr_code(self, url: str) -> ft.Control:
    import tempfile
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        img.save(tmp.name, format="PNG")
    
    return ft.Image(src=tmp.name, width=200, height=200, fit=ft.BoxFit.CONTAIN)
```

**Pending Improvements:**
- Add automatic URL copy to clipboard button
- Improve confirmation state UI
- Add retry option when OCR fails
- Show sample ticket image for reference

### Flet Web Mode Limitations
- **FilePicker does not work**: In Flet web mode (running inside Docker), `ft.FilePicker` fails because the JS handshake never completes. This is a known issue in Flet 0.81 web mode.
- **Solution**: Use the OCR microservice pattern with external HTML form
- **Impact**: Users must open the form in a new tab or scan QR code with phone

### Diagnostic Tool: check_flet.py
Before deploying or when experiencing UI errors, run the diagnostic tool:

```bash
# Local development
uv run python check_flet.py --compat

# In Docker container
docker exec auditor_familiar_app python /app/check_flet.py --compat
```

**What it checks:**
- FilePicker API (async, with_data, upload)
- Page.overlay, run_javascript
- ElevatedButton icon=/text= parameters
- **Card color= vs bgcolor=** (common error!)
- ft.Alignment vs ft.alignment
- UrlLauncher and launch_url deprecation
- SnackBar via overlay

**Example output:**
```
Card API --
  [OK] Card NO tiene color= — usar bgcolor= en el Container interno
  [OK] Card tiene bgcolor= (manera correcta)
```

### Configuration
- Environment variables in `.env` (copy from `.env.example`)
- Use `APP_ENV=production` to disable seed data
- Ollama runs on `http://localhost:11434` (or `http://host.docker.internal` in Docker)

---

## 3. Patterns & Conventions

### Observer Pattern (Event System)
- Use `EventSystem` for fire-and-forget operations (e.g., vectorization)
- Events are published but not awaited to avoid blocking UI

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

### Multi-Tenancy
- All queries must filter by `familia_id`
- Controllers accept optional `familia_id` parameter

### RAG (Retrieval-Augmented Generation)
- Knowledge files in `knowledge/` directory
- Vector memory stored in `ai_vector_memory` table
- Use `nomic-embed-text` for embeddings (768 dimensions)
- Use `gemma2:2b` for chat responses

---

## 4. Deuda Técnica — Auditoría 2026-03-05

Evaluación general: **8.5/10**. Arquitectura sólida con separación de capas, RAG, pgvector, observer pattern, Result[T,E] y tests. Los puntos siguientes son mejoras, no emergencias.

### TD-1 — AIController con lógica duplicada (PRIORIDAD ALTA)
**Archivo**: `controllers/ai_controller.py` (604 líneas, 27KB)

**Problema**: El bloque de construcción del `AIContext` (~90 líneas) está duplicado palabra por palabra entre `consultar_contador()` y `consultar_contador_stream()`. Bug corregido en un lugar no se corrige en el otro.

**Responsabilidades que no deberían estar en el controller:**
- `_detectar_rango_meses()` → parser NLP, debería ir en `services/`
- `_detectar_categorias_relevantes()` → NLP + fuzzy matching, debería ir en `services/`
- `_filtrar_gastos_por_contexto()` → lógica de negocio, debería ir en `services/`
- `_agrupar_gastos()` → transformación de datos, debería ir en `services/`
- `_calcular_subtotal_semantico()` → RAG + pgvector, debería ir en `services/`
- `_resumir_metodos_pago()` → lógica de negocio, debería ir en `services/`
- `CATEGORY_KEYWORDS` → 90 líneas de datos estáticos en el controller

**Fix mínimo (30 min)**: Extraer `_construir_contexto(pregunta, session) -> AIContext` y llamarlo desde ambos métodos públicos.

**Refactor completo (media sesión)**:
```
AIController
   ↓
AIQueryService
   ├─ PeriodDetector       (_detectar_rango_meses)
   ├─ CategoryDetector     (_detectar_categorias_relevantes)
   ├─ ExpenseAggregator    (_agrupar_gastos, _filtrar_gastos_por_contexto)
   └─ ContextBuilder       (construcción del AIContext)
```

---

### TD-2 — services/ sin separación de responsabilidades (PRIORIDAD MEDIA)
**Directorio**: `services/` (13 archivos mezclados)

**Problema**: Servicios de dominio, IA e infraestructura conviven en el mismo flat folder.

**Clasificación actual:**
- **Dominio**: `expense_service.py`, `income_service.py`, `family_member_service.py`, `shopping_service.py`, `auth_service.py`, `registration_service.py`, `validators.py`
- **IA/ML**: `ai_advisor_service.py` (15KB), `ia_memory_service.py`, `embedding_service.py`, `memory_event_handler.py`
- **Infraestructura**: `ocr_service.py`, `ticket_service.py`, `report_service.py`

**Estructura propuesta:**
```
services/
   domain/
       expense_service.py
       income_service.py
       ...
   ai/
       ai_advisor_service.py
       embedding_service.py
       ia_memory_service.py
       memory_event_handler.py
   infrastructure/
       ocr_service.py
       ticket_service.py
       report_service.py
```
**Nota**: Requiere actualizar todos los imports del proyecto. Hacer en una sola sesión con búsqueda/reemplazo global.

---

### TD-3 — _resultados en RAM sin TTL ✅ RESUELTO 2026-03-05
**Archivo**: `ocr_api/main.py` + `ocr_api/models.py`

**Solución implementada**: Tabla `ocr_sessions` en PostgreSQL — sin Redis, sin infra nueva.

**Tabla**:
```python
class OCRSession(Base):
    __tablename__ = "ocr_sessions"
    session_id: Mapped[str]      # PK
    familia_id: Mapped[int]
    resultado_json: Mapped[str | None]
    created_at: Mapped[datetime]
    expires_at: Mapped[datetime]  # TTL: created_at + 10 min
```

**Flujo**:
- `init_db()` en lifespan crea la tabla automáticamente al arrancar
- `_guardar_resultado_db()` persiste con `expires_at = now + 10min`
- `GET /resultado/{session_id}` lee y borra en una transacción (consume una sola vez)
- Background task `_cleanup_sesiones_expiradas()` limpia expiradas cada 5 min

**Ventajas vs dict en RAM**: persistente ante restart, TTL real, sin memory leak, escalable a múltiples workers.

---

### TD-4 — EventSystem singleton (PRIORIDAD BAJA)
**Archivo**: `core/events.py` línea 109

**Problema**: `event_system = EventSystem()` es un global de módulo. Tests que importan código que usa `event_system` arrastran handlers ya suscriptos.

**Mitigación existente**: `EventSystem.clear()` en línea 85 — llamar en fixtures de tests de integración.

**Fix futuro**: Dependency injection — pasar `event_system` como parámetro en lugar de importarlo directamente.

**Severidad actual**: Baja — los 247 tests pasan porque mockean la capa de servicios sin llegar al event system.

---

### TD-5 — Polling OCR → SSE (MEJORA FUTURA)
**Archivo**: `views/pages/ticket_upload_view.py` + `ocr_api/main.py`

Polling cada 2s es correcto para el caso de uso actual (app familiar, baja concurrencia). Cuando el proyecto escale, migrar a **Server-Sent Events (SSE)** — sin WebSocket, sin JS extra, HTTP estándar soportado por FastAPI y httpx.

**Implementación SSE cuando se decida migrar:**

FastAPI (`ocr_api/main.py`):
```python
from fastapi.responses import StreamingResponse

async def _resultado_stream(session_id: str):
    while True:
        if session_id in _resultados:
            data = json.dumps(_resultados.pop(session_id))
            yield f"data: {data}\n\n"
            break
        await asyncio.sleep(1)

@app.get("/resultado-stream/{session_id}")
async def stream_resultado(session_id: str):
    return StreamingResponse(
        _resultado_stream(session_id),
        media_type="text/event-stream",
    )
```

Flet (`ticket_upload_view.py`):
```python
async def _esperar_resultado_sse(self):
    async with httpx.AsyncClient(timeout=130.0) as client:
        async with client.stream(
            "GET",
            f"{_OCR_INTERNAL}/resultado-stream/{self._session_id}",
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    data = json.loads(line[5:])
                    self._procesar_resultado(data)
                    break
```

| Opción | Complejidad | Elegancia | Estado |
|--------|------------|-----------|--------|
| A — Polling 2s | ⭐ | ⭐ | **Implementado** |
| C — SSE | ⭐⭐ | ⭐⭐⭐⭐ | Pendiente (futuro) |

---

### Flet UI — Versión instalada (0.80+)
- **`ft.ElevatedButton` está DEPRECADO** desde v0.80.0 — usar `ft.Button`
- **`ft.OutlinedButton` está DEPRECADO** — usar `ft.Button` con estilo
- **`page.launch_url()` NO funciona en modo web** — usar `ft.Url` nativo en el botón
- **Abrir URL en nueva pestaña**: `ft.Button(url=ft.Url(url, target=ft.UrlTarget.BLANK))`
- **Link clickeable en texto**: `ft.Text(spans=[ft.TextSpan(text, url=url, style=ft.TextStyle(decoration=ft.TextDecoration.UNDERLINE))])`
- **`url_target` NO existe** como parámetro directo — encapsular en `ft.Url(url, target=...)`
- Siempre verificar API con `check_flet.py` antes de usar parámetros nuevos:
  ```bash
  # Local
  uv run python check_flet.py ElevatedButton
  uv run python check_flet.py --search url
  # En Docker
  docker exec auditor_familiar_app python check_flet.py --compat
  ```
