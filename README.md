# 🇺🇾 Contador Oriental

Sistema de gestión financiera familiar con **Python 3.12 + Flet + PostgreSQL + IA local (Ollama)**. Arquitectura enterprise con ABC, Generic, tipado estricto, y asistente contable que corre **100% offline** con memoria vectorial permanente (RAG).

---

## 🚀 Funcionalidades

- **🔐 Autenticación** — Login y registro de familias (hash Argon2id), multi-tenant completo
- **👨‍👩‍👧‍👦 Familia** — Personas (parentesco, edad, estado laboral) y mascotas
- **💰 Ingresos** — Por miembro, múltiples tipos (sueldo, jubilación, freelance, etc.)
- **💳 Gastos** — Categorías uruguayas, métodos de pago, recurrencia
- **📊 Dashboard** — Balance mensual automático, comparativa vs mes anterior por categoría
- **🤖 Contador Oriental** — Asistente IA local (Gemma 2:2b), streaming token a token, RAG con normativa uruguaya
- **🧠 Memoria Vectorial** — Cada gasto se vectoriza automáticamente; el Contador recuerda el historial completo con búsqueda semántica (pgvector + HNSW)
- **🔍 Búsqueda Semántica** — `expenses.embedding` vector(768): el subtotal se calcula por similitud cosine, no por keywords. "supermercado" encuentra "almacén", "verdulería", "delivery"
- **📅 Consultas Históricas** — Detecta automáticamente meses específicos ("octubre"), "mes pasado" y "últimos N meses" y carga los gastos reales de BD

---

## 🏗️ Arquitectura

### Capas del sistema

```
Views (Flet)
    │
Controllers  ──→  EventSystem (Observer)
    │                   │
Services             MemoryEventHandler
    │                   │
Repositories      EmbeddingService (nomic-embed-text)
    │                   │
PostgreSQL + pgvector
    ├── ai_vector_memory  (RAG: recuerdos de gastos)
    └── expenses.embedding (búsqueda cosine por descripción)
```

### Patrones y decisiones de diseño

- **`BaseTableRepository(ABC, Generic)`** — CRUD con mappers domain/table, filtro automático por `familia_id`
- **`BaseController`** — Context manager de sesión SQLAlchemy centralizado
- **`Result[T, E]`** — Manejo de errores sin excepciones en toda la capa de servicios
- **Observer Pattern** — `EventSystem` desacopla controllers de IA; agregar nuevos listeners sin tocar código existente
- **RAG (Retrieval-Augmented Generation)** — Cada consulta al Contador busca contexto semántico en pgvector antes de llamar a Gemma
- **Fire-and-forget** — La vectorización de gastos corre en background, nunca bloquea la UI

### Flujo de memoria vectorial y búsqueda semántica

```
Usuario guarda un gasto
    └─→ ExpenseController
            └─→ event_system.fire_and_forget(GASTO_CREADO)
                    └─→ [background] MemoryEventHandler
                                └─→ EmbeddingService → nomic-embed-text (768d)
                                        ├─→ MemoriaRepository → ai_vector_memory (RAG)
                                        └─→ ExpenseRepository → expenses.embedding

Usuario pregunta al Contador
    └─→ AIController
            ├─→ _detectar_rango_meses() → mes específico / últimos N / mes pasado
            ├─→ ExpenseRepository.get_by_month() → gastos históricos reales
            ├─→ _calcular_subtotal_semantico() → cosine search en expenses.embedding
            ├─→ buscar_contexto_para_pregunta() → HNSW cosine en ai_vector_memory
            └─→ AIAdvisorService → prompt enriquecido con contexto real
                    └─→ Gemma 2:2b → respuesta contextual sin alucinar números
```

---

## ⚡ Inicio Rápido

### Prerrequisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Ollama](https://ollama.com/) instalado en el host

### 1. Clonar y configurar

```bash
git clone https://github.com/Ponce1969/contador-oriental-ai.git
cd contador-oriental-ai

cp .env.example .env
# Editar .env con tus credenciales (ver sección Variables de Entorno)
```

### 2. Preparar modelos de IA

```bash
# Modelo principal del Contador Oriental
ollama pull gemma2:2b
ollama create contador-oriental -f Modelfile

# Modelo de embeddings para memoria vectorial (768 dimensiones, ~100MB)
ollama pull nomic-embed-text
```

### 3. Iniciar con Docker

```bash
docker compose up -d

# Ejecutar migraciones (incluye tabla vectorial y columna embedding)
uv run fleting db migrate

# Poblar datos de ejemplo (solo en APP_ENV=development)
$env:OLLAMA_BASE_URL="http://localhost:11434"
uv run fleting db seed

# Abrir aplicación
# http://localhost:8550
```

### Desarrollo local (sin Docker)

```bash
uv sync
# Levantar PostgreSQL con pgvector aparte, luego:
uv run fleting db migrate
uv run python main.py
```

---

## 🗄️ Base de Datos

### Tablas

| Tabla | Descripción |
|---|---|
| `familias` | Multi-tenant principal |
| `usuarios` | Login y autenticación |
| `family_members` | Miembros de la familia (personas y mascotas) |
| `incomes` | Ingresos por miembro |
| `expenses` | Gastos + columna `embedding vector(768)` para búsqueda semántica |
| `monthly_expense_snapshots` | Snapshots mensuales para comparativas |
| `ai_vector_memory` | Memoria vectorial RAG (pgvector, 768 dimensiones, índice HNSW) |
| `_fleting_migrations` | Control de versiones de migraciones |

### Migraciones

```bash
# Ver estado actual
uv run fleting db status

# Aplicar migraciones pendientes
uv run fleting db migrate

# Revertir última migración
uv run fleting db rollback

# Nueva migración
uv run fleting db make <nombre>
```

> **Importante:** La imagen Docker usa `pgvector/pgvector:pg16` (no `postgres:16-alpine`) para tener la extensión `vector` disponible.

---

## 🤖 IA Local — Contador Oriental

### Modelos necesarios

| Modelo | Uso | Tamaño |
|---|---|---|
| `contador-oriental` (Gemma 2:2b) | Genera respuestas en español rioplatense | ~1.5GB |
| `nomic-embed-text` | Vectoriza texto para memoria semántica | ~100MB |

### Cómo responde el Contador

El prompt que recibe Gemma tiene cuatro secciones opcionales:

```
1. NORMATIVA URUGUAYA RELEVANTE    ← RAG con archivos .md de knowledge/
2. REGISTROS HISTÓRICOS RELEVANTES ← RAG con pgvector (ai_vector_memory)
3. SUBTOTAL SEMÁNTICO              ← cosine search en expenses.embedding
4. ESTADO DE LA HACIENDA FAMILIAR  ← gastos reales del período calculados por Python
```

Gemma **nunca calcula** — solo narra los datos que Python le prepara. Esto evita alucinaciones numéricas.

### Detección de períodos históricos

```python
# El Contador entiende automáticamente:
"¿Cuánto gasté en supermercado el mes pasado?"   → carga gastos de enero/2026
"¿Cuál fue mi gasto más alto en octubre?"         → carga gastos de octubre/2025
"¿Cuánto gasté en salud en los últimos 3 meses?"  → carga dic/2025 + ene/2026 + feb/2026
```

### Configuración del modelo (`Modelfile`)

```dockerfile
FROM gemma2:2b
PARAMETER temperature 0.2
PARAMETER num_ctx 4096
PARAMETER num_predict 250
PARAMETER repeat_penalty 1.2
```

---

## 📁 Estructura del Proyecto

```
contador-oriental/
├── 📁 controllers/
│   ├── base_controller.py        # Context manager de sesión centralizado
│   ├── ai_controller.py          # Consultas al Contador con RAG vectorial
│   ├── expense_controller.py     # Gastos + publicación de eventos Observer
│   ├── income_controller.py
│   └── family_member_controller.py
├── 📁 services/
│   ├── ai_advisor_service.py     # Prompt builder + llamada a Ollama (streaming)
│   ├── embedding_service.py      # Genera vectores 768d con nomic-embed-text
│   ├── ia_memory_service.py      # Orquesta embedding + búsqueda semántica
│   ├── memory_event_handler.py   # Observer: vectoriza eventos en background
│   ├── expense_service.py
│   └── income_service.py
├── 📁 repositories/
│   ├── base_table_repository.py  # ABC + Generic con filtro por familia_id
│   ├── memoria_repository.py     # SQL directo con pgvector cosine distance
│   ├── expense_repository.py
│   └── income_repository.py
├── 📁 models/
│   ├── expense_model.py          # Pydantic con categorías uruguayas
│   ├── ai_model.py               # AIContext, AIRequest, CategoryMetric
│   └── memoria_model.py          # SQLAlchemy para ai_vector_memory
├── 📁 core/
│   ├── events.py                 # EventSystem Observer (async, fire-and-forget)
│   ├── router.py
│   ├── sqlalchemy_session.py
│   └── logger.py
├── 📁 seeds/
│   ├── initial.py                # Orquestador: essential_data siempre, dev-only el resto
│   ├── essential_data.py         # Datos críticos (familia base, idempotente)
│   ├── 001_gastos_ficticios.py   # 48 gastos de ejemplo en 4 meses
│   ├── 002_memoria_vectorial.py  # Embeddings en ai_vector_memory
│   └── 003_expense_embeddings.py # Embeddings en expenses.embedding
├── 📁 migrations/
│   ├── 001_initial.py … 005_*    # Migraciones previas
│   ├── 006_add_ai_vector_memory.py  # tabla ai_vector_memory + HNSW
│   └── 007_add_expense_embedding.py # columna expenses.embedding vector(768)
├── 📁 knowledge/
│   ├── irpf_familia_uy.md        # Normativa IRPF Uruguay
│   ├── inclusion_financiera_uy.md
│   └── ahorro_ui_uy.md
├── 📁 views/pages/
│   ├── ai_advisor_view.py        # Chat con el Contador (streaming)
│   ├── expenses_view.py
│   └── dashboard_view.py
├── 📁 tests/
│   ├── test_memoria_service.py   # 18 tests de memoria vectorial
│   └── test_validators.py / test_formatters.py / …
├── 📄 docker-compose.yml         # pgvector/pgvector:pg16 + app + pgAdmin
├── 📄 Modelfile                  # Parámetros del modelo contador-oriental
├── 📄 pyproject.toml             # uv + dependencias
└── 📄 main.py                    # Punto de entrada + wiring del Observer
```

---

## 🔧 Variables de Entorno

Copiar `.env.example` a `.env` y completar:

```bash
# Base de datos
DB_TYPE=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=auditor_familiar
POSTGRES_USER=postgres
POSTGRES_PASSWORD=tu_password_seguro

# Aplicación
SECRET_KEY=genera_con_python_secrets_token_hex_32
APP_ENV=production
DEBUG=false

# IA — URL de Ollama:
#   Dentro de Docker:  http://host.docker.internal:11434
#   Desarrollo local:  http://localhost:11434
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Memoria vectorial (desactivar si no tenés Ollama)
MEMORY_SERVICE_ENABLED=true

# Puertos
APP_PORT=8550
```

---

## 🧪 Tests y Calidad

```bash
# Tests de memoria vectorial (mocks, no requiere BD ni Ollama)
uv run pytest tests/test_memoria_service.py -v

# Todos los tests
uv run pytest -v

# Con cobertura
uv run pytest --cov=. --cov-report=html

# Type checking
uv run ty check .

# Linting
uv run ruff check .
```

**Cobertura actual:** 223 tests — memoria vectorial, búsqueda semántica, repositorios, servicios, validators, formatters, controllers e integración.

> Los tests de BD usan **PostgreSQL real** con transacciones revertidas por test (aislamiento sin contaminar datos).

---

## � Deploy en Orange Pi 5 Plus (ARM64)

```bash
# 1. Transferir archivos
rsync -avz --exclude '.venv/' --exclude 'logs/' \
  ./ user@orangepi:/opt/contador-oriental/

# 2. En el servidor
ssh user@orangepi
cd /opt/contador-oriental
cp .env.example .env  # Editar con credenciales de producción

# 3. Construir y levantar
docker compose build --no-cache app
docker compose up -d

# 4. Ejecutar migraciones
docker compose exec app uv run fleting db migrate
```

> La imagen `pgvector/pgvector:pg16` tiene builds para ARM64 — funciona nativamente en Orange Pi 5 Plus.

---

## 🛡️ Escudo Charrúa

| Pilar | Implementación |
|---|---|
| **Type Safety** | MyPy + tipado estricto en toda la base de código |
| **Error Handling** | `Result[T, E]` — sin excepciones silenciosas |
| **Resiliencia IA** | Si Ollama está apagado, los gastos se guardan igual |
| **Multitenancy** | `familia_id` obligatorio en todas las tablas y queries |
| **Sin bloqueos UI** | Toda la vectorización corre async en background |
| **Seeds seguros** | `APP_ENV=production` bloquea seeds de prueba automáticamente |
| **Code Quality** | Ruff, pre-commit hooks, imports ordenados |

---

## 🇺🇾 Características Uruguayas

- **Moneda** — Formato `$ 1.000` uruguayo
- **Categorías** — Almacén, UTE, ANTEL, OSE, IRPF, mutual, etc.
- **Normativa** — IRPF, inclusión financiera, ahorro en UI indexada
- **Idioma** — Español rioplatense (el Contador dice "¿en qué se te fue la plata?")

---

## 📄 Licencia

MIT License — Ver archivo [LICENSE](LICENSE) para detalles.

---

## 🤝 Contribuir

1. Fork del repositorio
2. Feature branch: `git checkout -b feature/nueva-funcionalidad`
3. Commit: `git commit -m 'feat: descripción clara del cambio'`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Pull Request

---

## 📞 Soporte

- 🐛 **Issues**: [GitHub Issues](https://github.com/Ponce1969/contador-oriental-ai/issues)
- 📧 **Email**: gompatri@gmail.com

---

**🇺🇾 Hecho con ❤️ en Uruguay para el control financiero familiar**
