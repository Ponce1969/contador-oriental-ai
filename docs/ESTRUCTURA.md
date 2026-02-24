# Estructura del Proyecto — Auditor Familiar

Sistema de gestión de finanzas familiares con Flet + PostgreSQL + IA local (Ollama).

---

## Organización de Carpetas

```
flet/
├── main.py                         # Punto de entrada
├── pyproject.toml                  # Dependencias (uv)
├── README.md                       # Documentación principal
├── Modelfile                       # Modelo Ollama personalizado (contador-oriental)
├── docker-compose.yml              # Orquestación Docker
├── Dockerfile                      # Imagen de la app
│
├── assets/                         # Recursos estáticos (iconos)
│
├── configs/
│   ├── app_config.py
│   ├── database_config.py          # SQLite (dev) / PostgreSQL (prod)
│   └── routes.py
│
├── core/
│   ├── logger.py
│   ├── router.py
│   ├── session.py                  # SessionManager (login/familia_id)
│   ├── sqlalchemy_session.py
│   └── state.py                    # AppState (device type para responsividad)
│
├── database/
│   ├── base.py
│   ├── engine.py
│   └── tables.py
│
├── models/
│   ├── ai_model.py                 # AIContext, AIRequest, AIResponse, CategoryMetric
│   ├── categories.py
│   ├── errors.py
│   ├── expense_model.py
│   ├── family_member_model.py
│   └── income_model.py
│
├── controllers/
│   ├── ai_controller.py            # Orquestador IA: prepara AIContext + streaming
│   ├── expense_controller.py
│   ├── family_member_controller.py
│   └── income_controller.py
│
├── services/
│   ├── ai_advisor_service.py       # RAG curado + Ollama async (stream y no-stream)
│   ├── expense_service.py
│   ├── family_member_service.py
│   ├── income_service.py
│   └── report_service.py
│
├── repositories/
│   ├── expense_repository.py
│   ├── family_member_repository.py
│   ├── income_repository.py
│   ├── monthly_snapshot_repository.py  # Comparativa mensual con LAG SQL
│   └── mappers.py
│
├── views/
│   ├── layouts/
│   │   └── main_layout.py          # Layout responsivo (mobile/tablet/desktop)
│   └── pages/
│       ├── ai_advisor_view.py      # Chat con streaming token a token
│       ├── dashboard_view.py
│       ├── expenses_view.py
│       ├── family_members_view.py
│       ├── incomes_view.py
│       └── login_view.py
│
├── knowledge/                      # RAG curado (archivos .md, máx 200 líneas c/u)
│   ├── ahorro_ui_uy.md
│   ├── inclusion_financiera_uy.md
│   └── irpf_familia_uy.md
│
├── migrations/
│   ├── migrate.py                  # CLI: migrate | rollback | status
│   ├── 001_initial.py
│   ├── 002_add_multiuser.py
│   ├── 003_restructure_family_members.py
│   ├── 004_add_pets_support.py
│   └── 005_add_monthly_snapshots.py  # Historial mensual para comparativa IA
│
├── docs/                           # Documentación técnica
│   ├── ESTRUCTURA.md               # Este archivo
│   ├── DOCKER_DEPLOYMENT.md
│   ├── POSTGRESQL_SETUP.md
│   └── VERIFICAR_PUERTOS.md
│
└── tests/
```

---

## Arquitectura MVC

```
Usuario → View → Controller → Service → Repository → Database
                     ↓
               AIController → AIAdvisorService → Ollama (contador-oriental)
                     ↓
               MonthlySnapshotRepository → PostgreSQL (LAG SQL)
```

Todos los servicios retornan `Result[T, AppError]`. La IA recibe datos pre-calculados por Python — nunca hace cálculos propios.

---

## Modelo de IA

- **Modelo**: `contador-oriental` (basado en `gemma2:2b`, Modelfile en raíz)
- **Parámetros**: `temperature 0.3`, `num_ctx 4096`, `num_predict 250`, `repeat_penalty 1.2`
- **RAG**: 3 archivos Markdown en `knowledge/` — selección por keywords
- **Streaming**: tokens via `ollama.AsyncClient` con buffer de 4 tokens en UI

### Crear el modelo en Ollama
```bash
ollama create contador-oriental -f Modelfile
```

---

## Responsividad

- Breakpoints: mobile `< 600px`, tablet `600–1024px`, desktop `> 1024px`
- `AppState.device` — detectado en `main.py` via `page.on_resize`
- Re-navegación automática al cambiar breakpoint

---

## Migraciones

```bash
# Dentro del contenedor Docker
docker exec auditor_familiar_app python -c "from migrations.migrate import migrate; migrate()"

# O directamente con uv (desarrollo local)
uv run python migrations/migrate.py migrate
uv run python migrations/migrate.py status
```

---

## Docker

```bash
# Rebuild y levantar
docker compose build --no-cache app && docker compose up -d

# Logs
docker compose logs --tail=20 app
```

- App: `http://localhost:8550`
- Ollama: corre en el host (`http://host.docker.internal:11434`)
- El código NO está montado como volumen — siempre requiere rebuild
