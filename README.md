# 🇺🇾 Contador Oriental

Sistema de gestión financiera familiar con **Python 3.12 + Flet + PostgreSQL + IA local (Ollama)**. Arquitectura enterprise con ABC, Generic, tipado estricto, y asistente contable que corre **100% offline** con memoria vectorial permanente (RAG).

---

## 🚀 Funcionalidades

- **🔐 Autenticación** — Login y registro de familias (hash Argon2id), multi-tenant completo
- **🔑 Recuperación de contraseña** — Reset por email con Resend, tokens de un solo uso con expiración de 1 hora, protección contra enumeración de emails
- **👨‍👩‍👧‍👦 Familia** — Personas (parentesco, edad, estado laboral) y mascotas
- **💰 Ingresos** — Por miembro, múltiples tipos (sueldo, jubilación, freelance, etc.)
- **💳 Gastos** — Categorías uruguayas, métodos de pago, recurrencia
- **📊 Dashboard** — Balance mensual automático, comparativa vs mes anterior por categoría
- **🤖 Contador Oriental** — Asistente IA local (Gemma 2:2b), streaming token a token, RAG con normativa uruguaya
- **🧠 Memoria Vectorial** — Cada gasto se vectoriza automáticamente; el Contador recuerda el historial completo con búsqueda semántica (pgvector + HNSW)
- **🔍 Búsqueda Semántica** — `expenses.embedding` vector(768): el subtotal se calcula por similitud cosine, no por keywords. "supermercado" encuentra "almacén", "verdulería", "delivery"
- **📅 Consultas Históricas** — Detecta automáticamente meses específicos ("octubre"), "mes pasado" y "últimos N meses" y carga los gastos reales de BD
- **📱 Soporte WhatsApp** — Botón de ayuda directo en la app (código Uruguay +598)
- **🛡️ Guardian** — Monitoreo automático de contenedores con alertas a Discord

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
- **Dependency Injection** — `EventSystem` inyectable en `BaseController`; producción usa el singleton, tests inyectan instancias limpias
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
docker compose up -d --build
```

> ✅ **Las migraciones se aplican automáticamente** al arrancar el contenedor `app`. No hace falta correr `fleting db migrate` a mano. Si la base ya está migrada, simplemente no hace nada.

Una vez que los 3 contenedores estén `healthy`:

```bash
# Poblar datos de ejemplo (solo en APP_ENV=development)
$env:OLLAMA_BASE_URL="http://localhost:11434"  # Windows PowerShell
# export OLLAMA_BASE_URL=http://localhost:11434  # Linux/macOS
uv run fleting db seed

# Abrir aplicación
# http://localhost:8550
```

> 💡 El seed es opcional y solo funciona con `APP_ENV=development` en el `.env`. En producción no hace nada.

### 4. Credenciales de desarrollo

La migración `002_add_multiuser.py` crea automáticamente un usuario administrador:

| Campo | Valor |
|-------|-------|
| **URL** | http://localhost:8550 |
| **Usuario** | `admin` |
| **Contraseña** | `admin123` |
| **Familia** | `Familia Principal` (`familia_id=1`) |

> ⚠️ **Importante para colaboradores:** Los seeds de datos ficticios (gastos de ejemplo, embeddings) se asignan siempre a la familia del usuario `admin` (`familia_id=1`). Para ver los datos del seed, iniciá sesión con `admin/admin123`. Si creás una familia nueva desde la UI, esa familia no tendrá datos de ejemplo.

### Desarrollo local (sin Docker)

```bash
uv sync
# Levantar PostgreSQL con pgvector aparte (ver docker-compose.yml para parámetros)
docker compose up -d postgres
# Migrar y arrancar:
uv run fleting db migrate
uv run python main.py
```

---

## 🐳 Comportamiento automático de Docker

Cada vez que se levanta con `docker compose up`, los contenedores hacen lo siguiente **sin intervención manual**:

| Contenedor | Qué hace al arrancar |
|---|---|
| `postgres` | Crea la base de datos si no existe. Healthcheck garantiza que está lista antes de que arranquen los otros. |
| `app` | Espera a Postgres → **aplica migraciones pendientes** → arranca Flet en `:8550` |
| `ocr_api` | Espera a Postgres → arranca FastAPI/uvicorn en `:8551` |

El comportamiento de las migraciones es **idempotente**: si ya están todas aplicadas, no toca nada.

```
git clone
   └── cp .env.example .env  (editar credenciales)
          └── docker compose up -d --build
                 └── ✅ App lista en http://localhost:8550
```

---

## �️ Base de Datos

### Tablas

| Tabla | Descripción |
|---|---|
| `familias` | Multi-tenant principal |
| `usuarios` | Login y autenticación (incluye `email` para recovery) |
| `password_reset_tokens` | Tokens de reseteo de contraseña (1hs TTL, un solo uso) |
| `family_members` | Miembros de la familia (personas y mascotas) |
| `incomes` | Ingresos por miembro |
| `expenses` | Gastos + columna `embedding vector(768)` para búsqueda semántica |
| `monthly_expense_snapshots` | Snapshots mensuales para comparativas |
| `ai_vector_memory` | Memoria vectorial RAG (pgvector, 768 dimensiones, índice HNSW) |
| `ocr_sessions` | Sesiones OCR temporales con TTL de 10 min (reemplaza dict en RAM) |
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
│   ├── __init__.py               # Re-exports para compatibilidad
│   ├── 📁 domain/                # Reglas de negocio puras
│   │   ├── expense_service.py
│   │   ├── income_service.py
│   │   ├── family_member_service.py
│   │   ├── auth_service.py
│   │   ├── registration_service.py
│   │   ├── shopping_service.py
│   │   └── validators.py
│   ├── 📁 ai/                    # Lógica de IA y embeddings
│   │   ├── ai_advisor_service.py # Prompt builder + llamada a Ollama (streaming)
│   │   ├── embedding_service.py  # Genera vectores 768d con nomic-embed-text
│   │   ├── ia_memory_service.py  # Orquesta embedding + búsqueda semántica
│   │   └── memory_event_handler.py  # Observer: vectoriza eventos en background
│   └── 📁 infrastructure/        # Integraciones externas
│       ├── ocr_service.py        # Tesseract + preprocesado OpenCV
│       ├── ticket_service.py     # Parseo de tickets con Gemma
│       └── report_service.py     # Generación de reportes PDF
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
POSTGRES_PASSWORD=tu_password_seguro   # ← cambiar siempre

# Aplicación
# ⚠️ EN SERVIDOR: production | EN LOCAL: development
APP_ENV=production
SECRET_KEY=genera_con_python_secrets_token_hex_32  # ← generar nueva siempre
DEBUG=False

# IA — URL de Ollama:
#   Dentro de Docker:  http://host.docker.internal:11434
#   Desarrollo local:  http://localhost:11434
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Memoria vectorial (desactivar si no tenés Ollama)
MEMORY_SERVICE_ENABLED=true

# Puertos
APP_PORT=8550

# Recuperación de contraseña (Resend)
RESEND_API_KEY=re_xxxxx           # API key de Resend (https://resend.com)
RESEND_FROM_EMAIL=app4@loquinto.com  # Email verificado en Resend
APP_BASE_URL=https://app4.loquinto.com  # URL pública de la app (para generar link de reset)
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

**Cobertura actual:** 247 tests — memoria vectorial, búsqueda semántica, repositorios, servicios, validators, formatters, controllers, OCR e integración.

> Los tests de BD usan **PostgreSQL real** con transacciones revertidas por test (aislamiento sin contaminar datos).

---

## 🚀 Deploy en Orange Pi 5 Plus (ARM64)

```bash
# 1. Clonar el repo en el servidor
ssh user@orangepi
git clone https://github.com/Ponce1969/contador-oriental-ai.git /opt/contador-oriental
cd /opt/contador-oriental

# 2. Configurar variables de entorno
cp .env.example .env
nano .env
# Asegurate de configurar:
#   POSTGRES_PASSWORD=tu_password_seguro
#   SECRET_KEY=genera_con: python -c "import secrets; print(secrets.token_hex(32))"
#   APP_ENV=production   ← MUY IMPORTANTE (ver abajo)
#   DEBUG=False

# 3. Levantar todo (migraciones incluidas, automáticas)
docker compose up -d --build
```

> ✅ No hace falta correr `fleting db migrate` — el entrypoint lo hace solo.

> La imagen `pgvector/pgvector:pg16` tiene builds para ARM64 — funciona nativamente en Orange Pi 5 Plus.

### ⚠️ Variable crítica: `APP_ENV`

| Valor | Cuándo usarlo | Efecto |
|---|---|---|
| `APP_ENV=production` | **Servidor / Orange Pi** | Bloquea `fleting db seed`. Sin datos de prueba. |
| `APP_ENV=development` | PC de desarrollo local | Permite `fleting db seed` con gastos de ejemplo. |

> 🚨 **Si dejás `APP_ENV=development` en el servidor** y alguien corre `fleting db seed` por accidente, se cargarán ~48 gastos ficticios en la base de producción. Siempre usar `production` en el servidor.

También generá una `SECRET_KEY` única para producción:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Actualizar a nueva versión

```bash
git pull
docker compose up -d --build
# Las migraciones nuevas se aplican solas al reiniciar
```

### Cloudflare Tunnel (acceso público para beta testers)

Si usás Cloudflare Tunnel para exponer el servidor, necesitás **dos túneles**:

| Túnel | Puerto local | URL pública ejemplo |
|---|---|---|
| App principal | `8550` | `https://app4.loquinto.com` |
| OCR microservicio | `8551` | `https://ocr.loquinto.com` |

> PostgreSQL (5432) **NO se expone** — solo se comunica internamente entre contenedores.

Configurar en el `.env` del servidor:

```bash
# URL pública del OCR — CRÍTICO para que el formulario de tickets funcione
# Debe ser la URL que el BROWSER del usuario puede alcanzar
OCR_API_PUBLIC_URL=https://ocr.loquinto.com

# URL interna — no cambiar
OCR_API_URL=http://ocr_api:8551
```

> ⚠️ Si `OCR_API_PUBLIC_URL` apunta a `localhost`, el link del formulario OCR
> no funcionará para los usuarios remotos (sus browsers no llegan al `localhost` del servidor).

#### Multi-tenant — aislamiento de familias

Cada familia solo ve sus propios datos. El `familia_id` se filtra en **todas** las queries:

```
Familia A (amigo 1) → familia_id=2 → solo ve sus gastos/ingresos
Familia B (amigo 2) → familia_id=3 → solo ve sus gastos/ingresos
admin              → familia_id=1 → solo ve sus gastos/ingresos
```

Cada familia crea su cuenta desde el registro en la UI. No necesitás crear cuentas manualmente.

---

## � Soporte y Monitoreo

### Botón de WhatsApp

Acceso directo a soporte desde cualquier pantalla de la app:

- **Número**: `+598 99 171 819` (Uruguay)
- **Mensaje predefinido**: *"Hola, necesito ayuda con Contador Oriental AI"*
- **Ubicación**: Top bar (icono verde 💬)

```python
# Implementación: views/layouts/main_layout.py
WhatsAppConfig(
    phone_number="99171819",
    default_message="Hola, necesito ayuda con Contador Oriental AI",
    country_code="598",
)
```

> ⚠️ **Nota técnica**: `page.launch_url()` es async en Flet web. Requiere `await` y manejo con `asyncio.create_task()` en callbacks de UI.

### Guardian — Monitoreo de Contenedores

Servicio independiente que vigila la salud de todos los contenedores Docker y envía alertas a Discord.

| Función | Descripción |
|---------|-------------|
| **Monitoreo** | Revisa cada 60s: `app`, `postgres`, `ocr_api` |
| **Alertas** | Notificación Discord si un contenedor cae o vuelve |
| **Auto-start** | Se levanta con `docker compose up` |

**Variables de entorno**:

```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
GUARDIAN_CHECK_INTERVAL=60  # segundos
```

**Estructura del proyecto**:

```
guardian/
├── guardian_service.py     # Servicio async de monitoreo
└── README.md               # Documentación específica
```

---

## �🛡️ Escudo Charrúa

| Pilar | Implementación |
|---|---|
| **Type Safety** | MyPy + tipado estricto en toda la base de código |
| **Error Handling** | `Result[T, E]` — sin excepciones silenciosas |
| **Resiliencia IA** | Si Ollama está apagado, los gastos se guardan igual |
| **Multitenancy** | `familia_id` obligatorio en todas las tablas y queries |
| **Sin bloqueos UI** | Toda la vectorización corre async en background |
| **Seeds seguros** | `APP_ENV=production` bloquea seeds de prueba automáticamente |
| **Code Quality** | Ruff, pre-commit hooks, imports ordenados |
| **OCR persistente** | Sesiones OCR en PostgreSQL (`ocr_sessions`) — resistentes a reinicios del contenedor |
| **EventSystem DI** | `EventSystem` inyectable en tests sin tocar el singleton global |

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

## 🏗️ Arquitectura OCR: Microservicio + BottomSheet inline

### Solución implementada

`ft.FilePicker` y `ft.UrlLauncher` **no funcionan en Flet 0.82 web** — son `Service` controls que dependen de un listener JS que no se registra en modo web. La solución usa un microservicio FastAPI separado con formulario HTML nativo, integrado en un **BottomSheet inline** dentro de la vista de gastos.

### Flujo completo (sin cambiar de página)

```
Vista Gastos :8550
    │  1. Botón cámara (FAB) → abre BottomSheet grande (~460px)
    │  2. BottomSheet muestra link al formulario + spinner
    │  3. Polling en background cada 2s
    ▼
Formulario HTML :8551/upload-form  (nueva pestaña al tocar el link)
    │  <input type="file" capture="environment"> nativo del browser
    │  Usuario saca foto → POST /upload-form-submit
    ▼
Microservicio OCR :8551
    │  OpenCV preprocesa imagen (resize×2, CLAHE, gaussian blur, deskew, threshold)
    │  Tesseract extrae texto + confianza  (--psm 6 --oem 3)
    │  Gemma2 parsea monto/fecha/comercio/items → JSON
    │  Guarda resultado en tabla ocr_sessions (PostgreSQL, TTL 10 min)
    ▼
BottomSheet (polling detecta resultado)
    │  El sheet muta automáticamente: spinner → campos editables
    │  Monto, fecha, descripción, categoría pre-llenados
    │  Indicador de confianza OCR (alta/media/baja)
    ▼
Botón "Guardar gasto" dentro del BottomSheet
    │  ExpenseController.add_expense() → sin salir de la vista de gastos
    ▼
PostgreSQL :5432
    └── gasto guardado + fila ocr_sessions eliminada + SnackBar ✅
```

### Pipeline OCR (OpenCV)

```python
img → resize ×2 (INTER_CUBIC) → CLAHE → GaussianBlur(3,3)
    → adaptiveThreshold(GAUSSIAN_C, 31, 2) → deskew → PIL → Tesseract
```

### Persistencia de sesiones OCR

Las sesiones ya **no se guardan en RAM** (`_resultados: dict`). Se persisten en PostgreSQL:

```sql
ocr_sessions(
    session_id  TEXT PRIMARY KEY,
    familia_id  INTEGER,
    resultado_json TEXT,
    created_at  TIMESTAMPTZ,
    expires_at  TIMESTAMPTZ   -- TTL: created_at + 10 min
)
```

- Resistente a reinicios del contenedor
- Cleanup automático cada 5 minutos
- Sesión consumida (DELETE) en el primer polling exitoso

### Servicios Docker

| Servicio | Puerto | Descripción |
|----------|--------|--------------|
| `app` | 8550 | App Flet principal |
| `ocr_api` | 8551 | Microservicio OCR FastAPI |
| `postgres` | 5432 | Base de datos |
| `guardian` | — | Monitoreo de salud + alertas Discord |

### Variables de entorno relevantes

| Variable | Default | Descripción |
|----------|---------|-------------|
| `OCR_API_URL` | `http://ocr_api:8551` | URL interna Docker (Flet→microservicio) |
| `OCR_API_PUBLIC_URL` | `http://localhost:8551` | URL pública (browser→formulario) |

### Limitación conocida de Flet 0.82 web

`ft.FilePicker`, `ft.UrlLauncher` y `page.launch_url()` son `Service` controls que dependen de un listener JS que **no se registra correctamente en Flet 0.82 web**. Se usa `ft.TextSpan(url=...)` como alternativa que sí funciona.

### ⚠️ Flet Web y deep links (query params)

Flet Web maneja las URLs de forma diferente a frameworks web tradicionales. Tres gotchas importantes:

1. **`page.route` incluye query params**: Cuando un usuario navega a `/reset-password?token=abc`, `page.route` llega como `/reset-password?token=abc` (no solo `/reset-password`). El Router debe hacer `route.split("?")[0]` antes de buscar en el diccionario de rutas.

2. **`QueryString.get()` lanza `KeyError`**: A diferencia de `dict.get(key)` que devuelve `None`, `page.query.get(key)` lanza `KeyError` si la key no existe. Además, `page.query` puede no estar poblado en el primer render de la sesión. Usar `try/except` y fallbacks que parseen `page.route` y `page.url`.

3. **`page.on_route_change` es obligatorio**: Para que los deep links funcionen en Flet Web, hay que registrar `page.on_route_change` y llamar a la lógica de navegación desde ahí, no solo en `main()`.

Ver `core/router.py` (`_strip_query`), `main.py` (`_navigate_to_route`, `on_route_change`) y `views/pages/reset_password_view.py` (3 métodos de extracción de token) para la implementación de referencia.

### Archivos relevantes

- `views/pages/expenses_view.py` — `_on_abrir_ocr()`, `_ocr_render_loading()`, `_ocr_render_confirm()`, `_polling_ocr()` — flujo completo embebido en BottomSheet
- `views/pages/ticket_upload_view.py` — vista OCR standalone (accesible también desde `/ticket-ocr`)
- `ocr_api/main.py` — endpoints `/upload-form`, `/upload-form-submit`, `/resultado/{id}`
- `ocr_api/config.py` — configuración Tesseract + Ollama
- `ocr_api/models.py` — `OCRSession` (SQLAlchemy), `OCRResponse`, `HealthResponse`
- `entrypoint.sh` — espera Postgres + migraciones automáticas (app)
- `ocr_api/entrypoint.sh` — espera Postgres (ocr_api)

---

**🇺🇾 Hecho con ❤️ en Uruguay para el control financiero familiar**
