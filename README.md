# Auditor Familiar de Gastos e Ingresos

Sistema de gestión financiera familiar con **Python 3.12 + Flet + PostgreSQL + IA local (Ollama)**. Arquitectura MVC con tipado estricto, errores como valores (`Result[T, E]`) y asistente contable que corre 100% offline.

---

## Funcionalidades

- **Autenticación**: Login y registro de familias (hash Argon2id), multi-tenant completo
- **Familia**: Personas (parentesco, edad, estado laboral) y mascotas
- **Ingresos**: Por miembro, múltiples tipos (sueldo, jubilación, freelance, etc.)
- **Gastos**: Categorías, subcategorías, métodos de pago, recurrencia
- **Dashboard**: Balance mensual automático, resumen por categoría
- **Contador Oriental**: Asistente IA local con `contador-oriental` (Gemma 2:2b tuneado), RAG con normativa uruguaya, streaming token a token, comparativa mensual de gastos

---

## Inicio rápido

### Docker (recomendado)

```bash
cp .env.example .env        # Configurar credenciales
docker compose up -d
# Abrir http://localhost:8550
```

### Desarrollo local

```bash
uv sync
uv run python migrations/migrate.py migrate
uv run python main.py
```

### Contador Oriental (IA)

```bash
# Requiere Ollama instalado en el host
ollama create contador-oriental -f Modelfile
# La app se conecta automáticamente a http://host.docker.internal:11434
```

---

## Documentación técnica

| Documento | Contenido |
|---|---|
| [`docs/ESTRUCTURA.md`](docs/ESTRUCTURA.md) | Arquitectura completa, carpetas, flujo de datos, comandos |
| [`docs/DOCKER_DEPLOYMENT.md`](docs/DOCKER_DEPLOYMENT.md) | Despliegue en Orange Pi 5 Plus y servidores ARM |
| [`docs/POSTGRESQL_SETUP.md`](docs/POSTGRESQL_SETUP.md) | Configuración de PostgreSQL en producción |
| [`docs/VERIFICAR_PUERTOS.md`](docs/VERIFICAR_PUERTOS.md) | Diagnóstico de red y puertos |
| [`Modelfile`](Modelfile) | Parámetros del modelo `contador-oriental` |

---

## Stack

- **UI**: Flet (Python)
- **BD**: PostgreSQL 16 (prod) / SQLite (dev) — SQLAlchemy 2.0
- **IA**: Ollama + `contador-oriental` (Gemma 2:2b, `temperature 0.3`, `num_ctx 4096`)
- **Deploy**: Docker Compose — listo para Orange Pi 5 Plus (ARM64)
- **Calidad**: Ruff, Mypy, `Result[T, E]` en toda la capa de servicios

---

## Licencia

MIT
