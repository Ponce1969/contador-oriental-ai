# 🇺🇾 Contador Oriental

Sistema integral de gestión financiera familiar con **Python 3.12 + Flet + PostgreSQL (pgvector) + IA local (Ollama)**. Diseñado bajo estándares de Clean Architecture con tipado estricto, operaciones monetarias 100% determinísticas en `Decimal` y un asistente contable que opera **completamente offline** con memoria vectorial permanente (RAG).

---

## 🚀 Funcionalidades Principales

- **🔐 Autenticación & Seguridad** — Login y registro de familias (hash Argon2id), control de sesiones, protección contra fuerza bruta y aislamiento multi-tenant estricto por `familia_id`.
- **🔑 Recuperación de Contraseña** — Reset por email con Resend y tokens criptográficos de un solo uso con expiración de 1 hora.
- **👨‍👩‍👧‍👦 Gestión Familiar & Actividades Económicas** — Integrantes del hogar con asignación de regímenes laborales: dependiente, servicios personales, Literal E, monotributo común/MIDES o pasividad.
- **🏛️ Optimizador IRPF Núcleo Familiar vs. Individual & Crédito por Alquiler (Ley 18.083 / Ley 18.719)** — Simulador anual con escalas oficiales de DGI: Escala A (ambos cónyuges generan rentas, MNI 14 BPC mensuales / 168 BPC anuales) vs. Escala B (un solo cónyuge genera rentas, MNI 8 BPC / 96 BPC anuales) vs. liquidación individual conjunta. Incluye cómputo automático del **8% de Crédito Fiscal por Alquiler** de vivienda permanente, deducciones por hijos menores de 18 años / con discapacidad y recomendación oficial con cuantificación del ahorro anual.
- **🐷 Metas de Ahorro Familiar (Alcancías)** — Creación de metas (viajes, emergencias, vehículos, reformas), registro de aportes por integrante y simulador de plazos temporales con inyección de aguinaldos legales.
- **🤝 Hogares Compartidos** — Gestión de gastos comunes entre múltiples familias (estilo Splitwise): pozo común, división proporcional o equitativa y liquidación automática de saldos.
- **💳 Compras en Cuotas** — Control de tarjetas de crédito, amortización mensual programada y seguimiento de cuotas restantes.
- **💱 Multi-moneda Dinámica (UYU / USD)** — Soporta Pesos Uruguayos (`$`) y Dólares (`USD`) con balances independientes y cotización diaria automática.
- **📊 Dashboard Financiero** — Métricas consolidadas en ambas monedas, comparativas mensuales y distribución por categorías.
- **🇺🇾 Motor Laboral y Tributario Uruguayo (100% Determinístico Decimal)**:
  - **Trabajo Dependiente**: Aguinaldo en dos cuotas (Ley 12.840), Salario Vacacional (Ley 16.101), Deducciones de Seguridad Social (Montepío 15% Ley 16.713/20.130, FONASA 3% a 8% Ley 18.211, FRL 0.1% Ley 18.406), IRPF Categoría II mensual y anual, y submotor de cálculo inverso (Líquido a Nominal) por bisección determinística ($\le \$0.01$).
  - **Servicios Personales / Independientes**: IVA servicios personales (22% / 10%) con retenciones CEDE (60%), IRPF anticipos bimestrales (con deducción ficta del 30% o gastos reales) y Caja Profesional CJPPU (10 categorías trienales al 16.5% Ley 17.738/20.212).
  - **Pequeña Empresa (Literal E)**: Control de tope anual de 305.000 UI con cotización dinámica, cuota mensual escalonada DGI (25% / 50% / 100% Ley 19.996) y aportes patronales BPS.
  - **Monotributo Común y Social MIDES**: Verificación de elegibilidad física ($\le 15\text{ m}^2$, $\le 1$ dependiente, topes 183.000 / 305.000 UI), cuota única BPS+DGI y escala de subsidio MIDES en 4 años ($25\%, 50\%, 75\%, 100\%$).
  - **Pasividades, Jubilaciones y Pensiones**: Liquidación de IASS con Mínimo No Imponible de 9 BPC (Ley 20.124), escala progresiva de 5 tramos, deducciones de salud (14% / 8%), retenciones FONASA pasivos (Ley 18.731) y consolidación multicaixa proporcional (BPS + Cajas Paraestatales).
- **🤖 Contador Oriental (IA Local con Ollama)** — Asistente explicativo local impulsado por Gemma 2:2b con streaming de respuestas. Principio rector: **Python calcula con 100% de precisión matemática y la IA explica el contexto legal**. Cada respuesta incorpora un descargo de responsabilidad jurídica orientativa.
- **🧠 Memoria Vectorial & Búsqueda Semántica** — Cada gasto se vectoriza en background (`expenses.embedding` vector(768) con `nomic-embed-text` + pgvector HNSW).
- **📷 Escaneo de Tickets OCR** — Microservicio FastAPI con OpenCV + Tesseract + Gemma2 para digitalización automática de recibos en BottomSheet inline.
- **📱 PWA & Soporte WhatsApp** — Instalable como Web App y botón de contacto de soporte directo en la barra superior.
- **🛡️ Guardian** — Monitoreo autónomo de salud de contenedores Docker y alertas a Discord.

---

## 🏗️ Arquitectura del Sistema

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
    ├── ai_vector_memory  (RAG: memoria y contexto)
    └── expenses.embedding (Búsqueda semántica por cosine distance)
```

### Patrones y Decisiones de Diseño

- **`BaseTableRepository(ABC, Generic)`** — CRUD genérico con mappers domain/table y filtrado estricto por `familia_id`.
- **`BaseController`** — Context manager centralizado de sesiones SQLAlchemy con manejo de transacciones.
- **`Result[T, E]`** — Manejo funcional de errores sin excepciones no controladas en la capa de servicios.
- **Observer Pattern** — `EventSystem` desacopla controladores de IA; la vectorización se ejecuta de forma asíncrona (*fire-and-forget*).
- **Dependency Injection** — Inyección de sesiones y repositorios facilitando pruebas unitarias aisladas sin mockeo sucio.
- **RAG (Retrieval-Augmented Generation)** — Cada consulta al Contador busca contexto semántico en pgvector antes de llamar a Gemma.
- **Zero White Backgrounds** — Interfaz visual con paleta pastel suave (`TEAL_50`, `PURPLE_50`, `AMBER_50`, bordes sutiles) reduciendo fatiga visual.

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
# Configurar las variables en .env (ver sección Variables de Entorno)
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

> ✅ **Las migraciones se aplican automáticamente** al arrancar el contenedor `app`. El entrypoint ejecuta `fleting db migrate` de forma idempotente.

Una vez que los contenedores estén activos:

```bash
# Poblar datos de ejemplo (solo en APP_ENV=development)
$env:OLLAMA_BASE_URL="http://localhost:11434"  # Windows PowerShell
# export OLLAMA_BASE_URL=http://localhost:11434  # Linux/macOS
uv run fleting db seed

# Abrir en el navegador
# http://localhost:8550
```

### 4. Credenciales por Defecto (Seed / Dev)

| Campo | Valor |
|-------|-------|
| **URL** | `http://localhost:8550` |
| **Usuario** | `admin` |
| **Contraseña** | `admin123` |
| **Familia** | `Familia Principal` (`familia_id=1`) |

---

## 🗄️ Base de Datos y Modelado

### Esquema de Tablas

| Módulo | Tablas | Descripción |
|---|---|---|
| **Core & Auth** | `familias`, `usuarios`, `password_reset_tokens` | Multi-tenant, cuentas de usuario y tokens seguros de recuperación |
| **Familia & Laboral** | `family_members`, `economic_activities`, `dependent_details`, `independent_details`, `literal_e_details`, `monotributo_details`, `pension_details` | Miembros, actividades económicas y parámetros fiscales/laborales uruguayos |
| **Finanzas Personales** | `incomes`, `expenses`, `monthly_expense_snapshots` | Ingresos, egresos categorizados, snapshots mensuales y vector embeddings |
| **Planes & Ahorro** | `savings_goals`, `savings_goal_contributions`, `installment_purchases`, `installment_payments` | Metas familiares de ahorro (alcancías), depósitos y compras en cuotas con tarjeta |
| **Hogares Compartidos** | `household_groups`, `household_members`, `household_shared_expenses`, `household_settlements` | Grupos multi-familiares, gastos compartidos y liquidaciones de saldos |
| **IA & Operaciones** | `ai_vector_memory`, `ai_usage_stats`, `ocr_sessions`, `exchange_rates`, `_fleting_migrations` | Memoria RAG pgvector (768d HNSW), métricas de uso de IA, sesiones OCR temporales y cotizaciones |

---

## 🤖 Contador Oriental (IA con RAG Local)

El prompt que recibe Gemma 2:2b se construye dinámicamente según la pregunta del usuario:

```
1. NORMATIVA URUGUAYA RELEVANTE    ← RAG desde archivos .md en knowledge/
2. CONTEXTO LABORAL & SUELDOS      ← Sueldos líquidos, aguinaldos y vacacionales pre-calculados
3. METAS DE AHORRO DEL HOGAR       ← Avance de alcancías y montos faltantes
4. MEMORIA VECTORIAL & REGISTROS   ← RAG en ai_vector_memory y cosine search en expenses.embedding
5. ESTADO DE LA HACIENDA FAMILIAR  ← Totales y comparativas mensuales calculados por Python
```

> 🛡️ **Invariante de Responsabilidad Jurídica:** Toda respuesta del asistente incorpora de forma preceptiva:
> *"Aviso: Este cálculo y explicación son de carácter meramente informativo y orientativo según la normativa vigente en Uruguay. No constituyen asesoramiento contable ni jurídico vinculante. Para decisiones formales o declaraciones juradas ante DGI/BPS/CJPPU, consulte a un profesional contable matriculado."*

---

## 📁 Estructura del Proyecto

```
contador-oriental/
├── 📁 controllers/
│   ├── base_controller.py            # Context manager de sesión centralizado
│   ├── ai_controller.py              # Orquestador del Asesor IA con RAG
│   ├── savings_goal_controller.py    # Metas de ahorro y simulación con aguinaldos
│   ├── installment_controller.py     # Cuotas de tarjeta de crédito
│   ├── household_controller.py       # Hogares compartidos y balances
│   ├── labor_controller.py           # Beneficios y deducciones laborales
│   ├── exchange_rate_controller.py   # Cotización USD/UYU
│   ├── expense_controller.py         # Gastos + Observer
│   ├── income_controller.py          # Ingresos
│   └── family_member_controller.py   # Integrantes del hogar
├── 📁 services/
│   ├── 📁 labor/                     # Submotor laboral y tributario uruguayo
│   │   ├── engine.py                 # Fachada LaborCalculationEngine
│   │   ├── labor_service.py          # Orquestador de dominio laboral
│   │   ├── 📁 domain/                # TaxRuleSets, DTOs inmutables
│   │   └── 📁 calculations/          # Algoritmos determinísticos (SAC, Vacacional, IRPF, IASS, CJPPU, etc.)
│   ├── 📁 domain/                    # Reglas de negocio puras
│   │   ├── savings_goal_service.py   # CRUD y simulador de metas de ahorro
│   │   ├── installment_service.py    # Gestión de compras en cuotas
│   │   ├── household_service.py      # Lógica de división de gastos comunes
│   │   ├── expense_service.py
│   │   ├── income_service.py
│   │   └── auth_service.py
│   ├── 📁 ai/                        # Lógica de IA y embeddings
│   │   ├── ai_advisor_service.py     # Prompt builder con streaming de Ollama
│   │   ├── embedding_service.py      # Vectores 768d con nomic-embed-text
│   │   └── ia_memory_service.py      # Búsqueda semántica en pgvector
│   └── 📁 infrastructure/            # Integraciones externas (OCR, PDFs, Cotización)
├── 📁 repositories/                  # Acceso a datos con BaseTableRepository
├── 📁 models/                        # Modelos Pydantic y DTOs
├── 📁 database/                      # Modelos SQLAlchemy y conexión
├── 📁 views/
│   ├── 📁 pages/                     # Vistas principales (Hogar, Dashboard, Planes, Familia, Gastos, etc.)
│   └── 📁 components/                # Componentes interactivos (FamilyIRPFOptimizerCard, SavingsGoalsCard, BenefitsCard, etc.)
├── 📁 migrations/                    # 001_initial.py ... 021_add_savings_goals.py
├── 📁 tests/                         # Suite automatizada con 470 tests unitarios e integración
├── 📄 docker-compose.yml             # postgres (pgvector) + app + ocr_api + guardian
├── 📄 Modelfile                      # Configuración del modelo contador-oriental
├── 📄 pyproject.toml                 # uv, dependencias y herramientas de calidad
└── 📄 main.py                        # Punto de entrada de la aplicación
```

---

## 🔧 Variables de Entorno

Copiar `.env.example` a `.env` y configurar:

```bash
# Base de datos
DB_TYPE=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=auditor_familiar
POSTGRES_USER=postgres
POSTGRES_PASSWORD=tu_password_seguro

# Aplicación (production en servidor / development en local)
APP_ENV=production
SECRET_KEY=generar_con_secrets_token_hex_32
DEBUG=False
APP_PORT=8550

# IA — URL de Ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
MEMORY_SERVICE_ENABLED=true

# Recuperación de contraseña (Resend)
RESEND_API_KEY=re_xxxxx
RESEND_FROM_EMAIL=app4@loquinto.com
APP_BASE_URL=https://app4.loquinto.com

# Microservicio OCR
OCR_API_URL=http://ocr_api:8551
OCR_API_PUBLIC_URL=https://ocr.loquinto.com

# Monitoreo Guardian
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
GUARDIAN_CHECK_INTERVAL=60
```

---

## 🧪 Tests y Calidad

El proyecto cuenta con una amplia suite de pruebas automatizadas:

```bash
# Ejecutar toda la suite de pruebas (470 tests)
uv run pytest -v

# Con reporte de cobertura de código
uv run pytest --cov=. --cov-report=html

# Verificación de tipos estáticos
uv run ty check .

# Linter y formato de código
uv run ruff check .
uv run ruff format --check .
```

> **Aislamiento de BD en pruebas:** Los tests de base de datos se ejecutan contra PostgreSQL real en transacciones aisladas que se revierten automáticamente al finalizar cada test.

---

## 🐳 Servicios en Docker

| Servicio | Puerto | Descripción |
|---|---|---|
| `postgres` | `5432` | PostgreSQL 16 con extensión `pgvector` (ARM64 & x86_64) |
| `app` | `8550` | Aplicación web Flet (FastAPI backend + interfaz interactiva) |
| `ocr_api` | `8551` | Microservicio de procesamiento OCR de comprobantes |
| `guardian` | — | Monitoreo continuo de contenedores y alertas en Discord |

---

## 📄 Licencia

MIT License — Ver archivo [LICENSE](LICENSE) para más detalles.

---

**🇺🇾 Hecho con ❤️ en Uruguay para el control financiero y tributario familiar.**
