# ARCHITECTURE_SPEC.md - Contador Oriental

## Tech Stack

| Component | Technology |
|-----------|------------|
| UI Framework | Flet 0.80+ |
| Web Framework | Flet-Web (FastAPI) |
| CLI Framework | Fleting (MVC) |
| Database | PostgreSQL + pgvector |
| ORM | SQLAlchemy |
| Validation | Pydantic |
| Error Handling | result (Result[T, E]) |
| OCR | Tesseract + pytesseract |
| AI Parsing | Ollama (Gemma2) |
| Embeddings | nomic-embed-text |
| Linting | ruff |
| Type Check | ty |
| Testing | pytest |

## Project Structure

```
├── controllers/     # Flet UI controllers + business logic
├── services/        # Business logic layer (no DB access)
│   ├── domain/     # Business rules
│   ├── ai/         # AI and embeddings
│   └── infrastructure/  # External integrations
├── repositories/    # Data access layer (DB queries)
├── models/         # Pydantic models, SQLAlchemy tables, errors
├── views/          # Flet UI pages
│   └── pages/     # Page views
├── core/           # Event system, routing, session
├── database/       # SQLAlchemy engine + tables
├── constants/      # Enums, messages, config
├── tests/          # pytest fixtures + test cases
├── migrations/     # fleting migrations
├── knowledge/     # RAG context files (Uruguayan tax law)
└── ocr_api/       # FastAPI microservice for OCR
```

## Container Architecture

### Docker Services
| Service | Port | Purpose |
|---------|------|---------|
| app | 8550 | Flet web application |
| ocr_api | 8551 | FastAPI OCR microservice |
| postgres | 5432 | PostgreSQL + pgvector |
| guardian | — | Health monitoring + Discord alerts |

### Internal Communication
- **Flet → OCR**: `http://auditor_familiar_ocr_api:8551`
- **OCR → Database**: Direct PostgreSQL connection
- **Flet → Database**: Direct PostgreSQL connection

## Key Patterns

### MVC with Fleting
- **Model**: SQLAlchemy tables + Pydantic validation
- **View**: Flet pages in `views/pages/`
- **Controller**: Business logic in `controllers/`

### Multi-Family Support
- Family registration and management
- Per-family data isolation (familia_id)
- Role-based access

### WhatsApp Support
- Direct support button in app header
- Pre-filled message with app name
- Uruguayan country code (+598)

### Event System (Observer Pattern)
- `EventSystem` for fire-and-forget operations
- Used for vectorization triggers
- Injected via BaseController

### Error Handling
- No exceptions in services/repositories
- Return `Result[T, E]` from `result` library
- Custom errors in `models/errors.py`

## Database Schema

### Core Tables
- `familias` - Family accounts
- `usuarios` - Users within families
- `gastos` - Expenses
- `ingresos` - Income
- `categorias_gastos` - Expense categories
- `ai_vector_memory` - RAG vector storage

### OCR Tables
- `ocr_sessions` - OCR processing sessions with TTL

## External Dependencies
- **Ollama**: `http://localhost:11434` (or `http://host.docker.internal`)
- **Tesseract**: Installed in ocr_api container

## Development Workflow

```bash
# Install deps
uv sync

# Start services
docker compose up -d

# Run migrations
uv run fleting db migrate

# Seed data (dev only)
uv run fleting db seed

# Run tests
uv run pytest -v

# Lint
uv run ruff check .
uv run ruff format .
```

## Environment Variables
- `DATABASE_URL` - PostgreSQL connection
- `OLLAMA_BASE_URL` - Ollama API endpoint
- `OCR_API_URL` - Internal OCR service
- `OCR_API_PUBLIC_URL` - Public OCR service
- `APP_ENV` - production/development
- `DISCORD_WEBHOOK_URL` - Guardian alerts
- `GUARDIAN_CHECK_INTERVAL` - Monitoring interval (seconds)
