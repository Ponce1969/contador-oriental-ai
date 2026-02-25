# 🇺🇾 Contador Oriental

Sistema de gestión financiera familiar con **Python 3.12 + Flet + PostgreSQL + IA local (Ollama)**. Arquitectura enterprise con ABC, Generic, tipado estricto, y asistente contable que corre 100% offline.

---

## 🚀 Funcionalidades Principales

- **🔐 Autenticación**: Login y registro de familias (hash Argon2id), multi-tenant completo
- **👨‍👩‍👧‍👦 Familia**: Personas (parentesco, edad, estado laboral) y mascotas
- **💰 Ingresos**: Por miembro, múltiples tipos (sueldo, jubilación, freelance, etc.)
- **💳 Gastos**: Categorías uruguayas, métodos de pago, recurrencia
- **📊 Dashboard**: Balance mensual automático, resumen por categoría
- **🤖 Contador Oriental**: Asistente IA local con `contador-oriental` (Gemma 2:2b), RAG con normativa uruguaya, streaming token a token

---

## 🏗️ Arquitectura

- **BaseTableRepository(ABC, Generic)** — Patrón repository con mappers específicos
- **BaseController** — Manejo de sesiones SQLAlchemy con tipado estricto
- **Validators** — `Result[T, E]` para validación robusta
- **Formatters** — Formato uruguayo consistente (`$ 1.000`)
- **Tests** — 33 tests críticos con 100% cobertura en componentes clave

---

## ⚡ Inicio Rápido

### Docker (Recomendado)

```bash
# 1. Clonar repositorio
git clone https://github.com/tu-usuario/contador-oriental.git
cd contador-oriental

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 3. Iniciar con Docker
docker compose up -d

# 4. Abrir aplicación
# Navegar a: http://localhost:8550
```

### Desarrollo Local

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

## 🧪 Tests y Calidad

```bash
# Ejecutar tests críticos
uv run pytest tests/test_validators.py tests/test_formatters.py -v

# Tests con cobertura
uv run pytest --cov=. --cov-report=html

# Type checking
uv run ty check .

# Linting
uv run ruff check .
```

---

## 🤖 IA Local (Ollama)

El Contador Oriental usa Gemma 2:2b tuneado para finanzas uruguayas:

```bash
# Descargar modelo
ollama pull gemma2:2b

# Crear modelfile personalizado
echo "FROM gemma2:2b
PARAMETER temperature 0.7
PARAMETER top_p 0.9
SYSTEM Eres el Contador Oriental, un asesor financiero especializado en Uruguay..." > Modelfile

# Construir modelo
ollama create contador-oriental -f Modelfile
```

---

## 📱 Deploy Manual (Orange Pi 5 Plus)

Para deployment en Orange Pi 5 Plus detrás de Cloudflare:

```bash
# 1. Transferir archivos
rsync -avz --exclude 'logs/' --exclude 'scripts/' --exclude 'docs/' \
  ./ user@orangepi:/opt/contador-oriental/

# 2. Configurar entorno
ssh user@orangepi
cd /opt/contador-oriental
cp .env.production .env

# 3. Construir y ejecutar
docker compose build --no-cache app
docker compose up -d

# 4. Configurar Cloudflare Tunnel
# Crear tunnel para puerto 8550
```

---

## 🔧 Configuración

### Variables de Entorno (.env)

```bash
# Base de datos
POSTGRES_DB=contador_oriental
POSTGRES_USER=contador_user
POSTGRES_PASSWORD=tu_password_seguro

# Aplicación
SECRET_KEY=tu_secret_key_32_caracteres
DEBUG=false

# Ollama (IA local)
OLLAMA_BASE_URL=http://localhost:11434
```

---

## 📁 Estructura del Proyecto

```
contador-oriental/
├── 📁 controllers/          # Lógica de negocio
├── 📁 services/            # Servicios y validators
├── 📁 repositories/        # Repositorios con ABC
├── 📁 models/              # Modelos Pydantic
├── 📁 views/               # Interfaz Flet
├── 📁 database/            # SQLAlchemy y migraciones
├── 📁 utils/               # Formatters y helpers
├── 📁 tests/               # Tests automatizados
├── 📄 docker-compose.yml   # Configuración Docker
├── 📄 pyproject.toml       # Dependencias Python
└── 📄 main.py              # Punto de entrada
```

---

## 🛡️ Escudo Charrúa

Arquitectura robusta con:
- **ABC + Generic** — Clases abstractas y generics
- **Type Safety** — MyPy y tipado estricto
- **Error Handling** — Result[T, E] pattern
- **Test Coverage** — 33 tests críticos
- **Code Quality** — Ruff, Typer, pre-commit hooks

---

## 🇺🇾 Características Uruguayas

- **Moneda**: Formato `$ 1.000` uruguayo
- **Categorías**: Gastos típicos uruguayos
- **Normativa**: IRPF, inclusion financiera, ahorro UI
- **Idioma**: Español uruguayo por defecto

---

## 📄 Licencia

MIT License — Ver archivo [LICENSE](LICENSE) para detalles.

---

## 🤝 Contribuir

1. Fork del repositorio
2. Feature branch: `git checkout -b feature/nueva-funcionalidad`
3. Commit: `git commit -m 'Agregar nueva funcionalidad'`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Pull Request

---

## 📞 Soporte

- 🐛 **Issues**: [GitHub Issues](https://github.com/tu-usuario/contador-oriental/issues)
- 💬 **Discusiones**: [GitHub Discussions](https://github.com/tu-usuario/contador-oriental/discussions)
- 📧 **Email**: gompatri@gmail.com

---

**🇺🇾 Hecho con ❤️ en Uruguay para el control financiero familiar**
