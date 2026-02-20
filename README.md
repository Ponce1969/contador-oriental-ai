# � Auditor Familiar de Gastos e Ingresos

Aplicación de escritorio construida con **Python 3.12**, **Flet**, **Fleting** y **arquitectura MVC** para gestión completa de finanzas familiares.

Sistema profesional de seguimiento de ingresos y gastos con balance automático, diseñado siguiendo **buenas prácticas profesionales**, con tipado estricto, separación de responsabilidades y manejo explícito de errores mediante `Result[T, E]`.

**🚀 Basado en Fleting Framework** - Micro framework MVC para Flet con routing automático, layouts consistentes y CLI productiva.

---

## 🎯 Objetivo del proyecto

Sistema completo de gestión financiera familiar que permite:

### **Funcionalidades Implementadas** ✅

* **� Sistema de Autenticación**: Login y registro de familias con hash Argon2
* **�👥 Gestión de Familia**: Registrar personas (parentesco, edad, estado laboral) y mascotas (especie)
* **💰 Gestión de Ingresos**: Registrar ingresos por miembro con múltiples tipos (sueldo, jubilación, renta, freelance, etc.)
* **💸 Gestión de Gastos**: Registrar gastos familiares con categorías, subcategorías y métodos de pago
* **📊 Dashboard**: Balance automático mensual (Ingresos - Gastos) con indicadores visuales
* **✏️ Edición completa**: Editar y eliminar todos los registros
* **🇺🇾 Formato uruguayo**: Montos con separador de miles ($50.000)
* **📈 Resúmenes**: Análisis por categorías con barras de progreso y porcentajes
* **🐾 Soporte para mascotas**: Incluye mascotas como miembros de la familia con gastos asociados
* **🤖 Contador Oriental (IA Local)**: Asistente contable con Gemma 2:2b vía Ollama, RAG con normativa uruguaya, chat premium con animaciones

---

## 🧱 Principios técnicos

Este proyecto sigue de forma estricta los siguientes principios:

* **Python moderno (3.12)**
* **Tipado estático estricto** (sin `Any`)
* **Arquitectura MVC real con Fleting**
* **Dominio desacoplado de la infraestructura**
* **Sin `try/except` para flujo normal**
* **Errores como valores (`Result[T, E]`)**

La aplicación está pensada para crecer sin necesidad de reescrituras importantes.

---

## 🧩 Arquitectura general (MVC)

La aplicación se divide en capas claras:

### Model

* Modelos de dominio con **Pydantic**
* Representan conceptos del negocio (ej: `ShoppingItem`)
* No conocen ni la UI ni la base de datos

### View

* Construida con **Flet**
* Solo se encarga de mostrar información y capturar eventos
* No contiene lógica de negocio ni SQL

### Controller

* Orquesta la comunicación entre la vista y los servicios
* No toma decisiones de negocio

### Service

* Contiene las reglas del dominio
* Valida invariantes
* Devuelve `Result` en lugar de lanzar excepciones

### Repository

* Encapsula el acceso a la base de datos
* Traduce entre ORM y dominio
* Aísla completamente SQLAlchemy

---

## 📂 Estructura del proyecto

```text
├── main.py                           # Punto de entrada (Fleting)
├── models/                           # Modelos de dominio (Pydantic)
│   ├── expense_model.py              # Modelo de gastos
│   ├── income_model.py               # Modelo de ingresos
│   ├── family_member_model.py        # Modelo de miembros
│   ├── categories.py                 # Categorías y enums
│   └── errors.py                     # Errores de dominio
├── views/                            # Vistas Flet (UI)
│   └── pages/
│       ├── dashboard_view.py         # Dashboard principal
│       ├── family_members_view.py    # Gestión de familia
│       ├── incomes_view.py           # Gestión de ingresos
│       ├── expenses_view.py          # Gestión de gastos
│       ├── home_view.py              # Página de inicio
│       └── settings_view.py          # Configuraciones
├── controllers/                      # Controladores MVC
│   ├── expense_controller.py
│   ├── income_controller.py
│   └── family_member_controller.py
├── services/                         # Lógica de negocio
│   ├── expense_service.py
│   ├── income_service.py
│   └── family_member_service.py
├── repositories/                     # Persistencia
│   ├── expense_repository.py
│   ├── income_repository.py
│   ├── family_member_repository.py
│   └── mappers.py                    # Mappers ORM ↔ Dominio
├── database/                         # Infraestructura BD
│   ├── base.py
│   └── tables.py                     # Tablas SQLAlchemy
├── core/                             # Núcleo de Fleting
│   ├── sqlalchemy_session.py
│   └── router.py
├── configs/                          # Configuraciones
│   ├── routes.py                     # Rutas de la app
│   └── app_config.py
├── flet_types/                       # Tipos correctos Flet
│   └── flet_types.py
├── knowledge/                        # Base de conocimiento RAG (Contador Oriental)
│   ├── inclusion_financiera_uy.md    # Ley de Inclusión Financiera (IVA débito/crédito)
│   ├── irpf_familia_uy.md            # IRPF: deducciones familia uruguaya
│   └── ahorro_ui_uy.md              # Ahorro en Unidades Indexadas
└── models/
    └── ai_model.py                   # AIContext, AIRequest, AIResponse, ChatMessage
```

---

## 🗄️ Base de datos

* Base de datos: **SQLite** (desarrollo) / **PostgreSQL** (producción)
* ORM: **SQLAlchemy 2.0**
* Estilo declarativo moderno
* **Multi-tenant**: Aislamiento completo por familia

### Configuración

La aplicación soporta dos modos:

**Desarrollo (SQLite)**
```bash
# .env
DB_TYPE=sqlite
SQLITE_DB_PATH=shopping.db
```

**Producción (PostgreSQL)**
```bash
# .env
DB_TYPE=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=auditor_familiar
POSTGRES_USER=tu_usuario
POSTGRES_PASSWORD=tu_password
```

**📖 Ver [docs/POSTGRESQL_SETUP.md](docs/POSTGRESQL_SETUP.md) para guía completa de PostgreSQL**

### Seguridad Multi-Tenant

- **Sistema de autenticación**: Login con usuario/contraseña (hash Argon2id)
- **Auto-registro**: Las familias pueden registrarse desde la aplicación
- Cada familia tiene su propio `familia_id`
- Todas las queries filtran automáticamente por familia
- Los usuarios solo ven datos de su familia
- Aislamiento completo en: `usuarios`, `family_members`, `incomes`, `expenses`

### Estructura de Tablas

**`familias`**
- `id`, `nombre`, `email`, `activo`, `created_at`

**`usuarios`**
- `id`, `familia_id`, `username`, `password_hash`, `nombre_completo`, `activo`, `created_at`

**`family_members`** (Personas y Mascotas)
- `id`, `familia_id`, `nombre`, `tipo_miembro` (persona/mascota)
- **Para personas**: `parentesco`, `edad`, `estado_laboral`
- **Para mascotas**: `especie`, `edad`
- `activo`, `notas`

**`incomes`**
- `id`, `familia_id`, `family_member_id`, `tipo_ingreso`
- `monto`, `fecha`, `categoria`, `descripcion`
- `es_recurrente`, `frecuencia`, `notas`

**`expenses`**
- `id`, `familia_id`, `monto`, `fecha`, `descripcion`
- `categoria`, `subcategoria`, `metodo_pago`
- `es_recurrente`, `frecuencia`, `notas`

El dominio **no depende del ORM**: se utilizan mappers explícitos para traducir entre tablas y modelos Pydantic.

---

## ⚠️ Manejo de errores

En lugar de excepciones, el proyecto utiliza el tipo:

```python
Result[T, E]
```

Donde:

* `T` es el valor esperado
* `E` es un error explícito del dominio o la infraestructura

Esto permite:

* Código predecible
* Tests más simples
* UI sin `try/except`

---

## 🚀 Flujo actual de la aplicación

1. El usuario interactúa con la **vista Flet**
2. La vista envía eventos al **controller**
3. El controller llama al **service**
4. El service valida reglas y delega al **repository**
5. El repository persiste en SQLite y devuelve un `Result`
6. La vista reacciona al resultado

---

## 🚀 Instalación y Uso

### **Opción 1: Docker (Recomendado para producción)**

Ideal para desplegar en Orange Pi 5 Plus o cualquier servidor ARM64/x86_64.

```bash
# Clonar el repositorio
git clone <tu-repo-url>
cd flet

# Configurar variables de entorno
cp .env.example .env
nano .env  # Editar con credenciales reales

# Desplegar con script automático
chmod +x deploy.sh
./deploy.sh

# O manualmente
docker compose up -d

# Ejecutar migraciones
docker exec auditor_familiar_app python migrations/migrate.py migrate

# Ver logs
docker compose logs -f
```

**📖 Ver [docs/DOCKER_DEPLOYMENT.md](docs/DOCKER_DEPLOYMENT.md) para guía completa de Docker**

### **Opción 2: Instalación local (Desarrollo)**

**Requisitos previos:**
* Python 3.12+
* uv (gestor de paquetes)

```bash
# Clonar el repositorio
git clone <tu-repo-url>
cd flet

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales (ver sección Base de datos)

# Instalar dependencias con uv
uv sync

# Ejecutar migraciones (primera vez)
uv run python migrations/migrate.py migrate

# Ejecutar la aplicación
uv run python main.py
```

**⚠️ IMPORTANTE:** El archivo `.env` contiene credenciales sensibles y **NO debe subirse a GitHub**. Ya está incluido en `.gitignore`.

### **Comandos CLI de Fleting**

Fleting incluye una CLI productiva para generar código:

```bash
# Ver ayuda general
fleting -h

# Crear una nueva vista
fleting create view nombre_vista

# Crear un nuevo controlador
fleting create controller nombre_controller

# Crear un nuevo modelo
fleting create model nombre_model

# Ver todas las rutas registradas
fleting routes

# Generar scaffold completo (modelo + vista + controller)
fleting scaffold nombre_entidad
```

### **Flujo de uso de la aplicación**

1. **Registro e Inicio de Sesión**
   - Crea una cuenta nueva desde "¿No tienes cuenta? Regístrate aquí"
   - Completa: nombre de familia, email, admin username, contraseña
   - Inicia sesión con tus credenciales

2. **Configura tu familia** en 👥 Familia
   - **Personas**: Agrega miembros con parentesco, edad y estado laboral
     - Padre, Madre, Hijo/Hija, Abuelo/Abuela, Otro
     - Estado: Empleado, Desempleado, Jubilado, Estudiante, Independiente
   - **Mascotas**: Agrega tus mascotas con especie y edad
     - Gato, Perro, Pájaro, u otra especie (texto libre)

3. **Registra ingresos** en 💰 Ingresos
   - Selecciona el miembro de la familia
   - Tipo de ingreso: Sueldo, Jubilación, Renta, Freelance, Bono, Subsidio
   - Indica monto, fecha y si es recurrente

4. **Registra gastos** en 💸 Gastos
   - Selecciona categoría y subcategoría
   - Indica método de pago (Efectivo, Tarjeta, Transferencia)
   - Marca si es recurrente (mensual, quincenal, anual)

5. **Consulta el balance** en 📊 Dashboard
   - Ve el balance del mes actual
   - Analiza ingresos vs gastos por categoría
   - Identifica patrones de gasto familiar

6. **Consultá al Contador Oriental** en 🤖 Contador Oriental
   - Usá los chips de acceso rápido (IVA, Débito/Crédito, Alquiler, Resumen)
   - O escribí tu consulta libre y presioná Enter o el botón de envío
   - El contador analiza tus gastos reales del mes y responde en español rioplatense
   - Marcá "Incluir mis gastos del mes" para que la IA tenga contexto financiero real

---

---

## 🤖 Contador Oriental — Asistente IA Local

El **Contador Oriental** es un asistente contable integrado que corre 100% local usando **Gemma 2:2b** vía **Ollama**. No envía datos a ningún servidor externo.

### Arquitectura del Contador Oriental

```
Usuario (Flet UI)
    │  async/await
    ▼
AIController.consultar_contador()   ← async def
    │  Consultas síncronas a BD (SQLAlchemy)
    │  Construye AIContext con datos pre-calculados
    ▼
AIAdvisorService.consultar()        ← async def
    │  ollama.AsyncClient (no bloquea el event loop)
    │  Construye prompt con datos reales
    ▼
Gemma 2:2b (Ollama local)
    │  Solo narra, NUNCA calcula
    ▼
Respuesta en el chat
```

### Principio fundamental: Python calcula, Gemma narra

Gemma 2:2b es un modelo pequeño propenso a errores de cálculo. Por eso:

- **Python pre-calcula** todos los totales, balances, subtotales y per cápita
- **`AIContext`** (Pydantic model) agrupa todos los datos financieros del mes
- **Gemma solo lee** el contexto y lo narra en español rioplatense
- El prompt incluye instrucción explícita: *"NUNCA sumes ni calcules nada"*

### AIContext — Datos pre-calculados

```python
class AIContext(BaseModel):
    resumen_gastos: dict          # Gastos agrupados por categoría/descripción
    total_gastos_count: int       # Cantidad de transacciones
    total_gastos_mes: float       # Total real del mes (para balance correcto)
    ingresos_total: float         # Total de ingresos
    miembros_count: int           # Miembros de la familia
    resumen_metodos_pago: str     # Ej: "Efectivo: 6 compras (85%), Tarjeta débito: 1 (14%)"
```

### RAG — Retrieval Augmented Generation

Se incluye normativa uruguaya **solo cuando la pregunta es relevante**:

| Archivo | Se activa con |
|---|---|
| `inclusion_financiera_uy.md` | iva, tarjeta, débito, crédito, descuento |
| `irpf_familia_uy.md` | irpf, impuesto, alquiler, hijo, hipoteca, dgi |
| `ahorro_ui_uy.md` | ahorro, ui, unidad indexada, inflación, plazo fijo |

Cuando hay datos financieros reales, el prompt instruye a Gemma a **priorizar los datos del usuario** sobre la normativa general.

### Detección inteligente de categorías

- **Fuzzy matching** (`difflib`) para tolerar errores tipográficos ("alamcen" → "Almacén")
- **Tokenización estricta** (`re.findall`) para evitar falsos positivos ("gastos" no activa "Hogar" por contener "gas")
- Detección de frases compuestas ("seguro auto", "tarjeta débito")

### Chat UI Premium

- **Burbujas con Markdown**: Gemma puede responder con listas, negritas, etc.
- **Quick chips**: 4 accesos rápidos (IVA, Débito/Crédito, Alquiler, Resumen)
- **Typing indicator**: Tres puntos animados con efecto onda mientras Gemma responde
- **Ancho controlado** (`width=500`): Las burbujas no se estiran en pantallas anchas
- **Bordes asimétricos**: Estilo iMessage/WhatsApp según el emisor
- **Auto-scroll**: El chat baja automáticamente al último mensaje
- **Enter para enviar**: `on_submit` en el TextField

### Requisitos para el Contador Oriental

```bash
# Instalar Ollama (https://ollama.com)
curl -fsSL https://ollama.com/install.sh | sh

# Descargar el modelo
ollama pull gemma2:2b

# En Docker, Ollama debe estar corriendo en el host
# La app se conecta a: http://host.docker.internal:11434
```

---

## 🛣️ Roadmap de mejoras futuras

### **Funcionalidades pendientes** 🔮

* **📄 Exportar chat a PDF**: Descargar el análisis del Contador Oriental en PDF
* **📅 Selector de mes/año**: Ver balance de meses anteriores
* **📊 Gráficos avanzados**: Gráficos de línea, torta, evolución mensual
* **🔔 Alertas**: Notificaciones cuando gastos superan presupuesto
* **💾 Exportar datos**: Exportar a Excel/CSV para análisis externo
* **🎯 Presupuestos**: Definir presupuestos por categoría
* **📱 Versión móvil**: Adaptar para Android/iOS con Flet
* ** Sincronización**: Sync entre dispositivos (cloud)
* **📈 Proyecciones**: Predicción de gastos futuros con IA
* **🏦 Integración bancaria**: Importar movimientos automáticamente
* **📸 Recibos**: Adjuntar fotos de tickets/facturas
* **🔍 Búsqueda avanzada**: Filtros por fecha, monto, categoría
* **📊 Comparativas**: Comparar meses/años anteriores
* **� Gestión de vehículos**: Tabla dedicada para vehículos y sus gastos
* **🏠 Gestión de propiedades**: Tabla para propiedades (alquileres, impuestos)

---

## 🧠 Público objetivo

* Personas que quieren controlar sus gastos
* Familias
* Desarrolladores Python que quieran aprender:

  * Flet
  * Arquitectura limpia
  * Tipado moderno

---

## 🚀 Flujo actual de la aplicación

1. El usuario interactúa con la **vista Flet** (routing automático de Fleting)
2. La vista envía eventos al **controller**
3. El controller llama al **service** usando sesión de SQLAlchemy
4. El service valida reglas y delega al **repository**
5. El repository persiste en SQLite y devuelve un `Result`
6. La vista reacciona al resultado

---



## ✅ Estado actual

✔ ✅ **Sistema de autenticación con registro y login**
✔ ✅ **Multi-tenant con aislamiento completo por familia**
✔ ✅ **Gestión de personas (parentesco, edad, estado laboral)**
✔ ✅ **Soporte para mascotas (especie, edad)**
✔ ✅ **Módulo de Ingresos asociados a miembros**
✔ ✅ **Módulo de Gastos con categorías y subcategorías**
✔ ✅ **Dashboard con balance automático mensual**
✔ ✅ **Formato uruguayo con separador de miles**
✔ ✅ **Arquitectura MVC con tipado estricto**
✔ ✅ **PostgreSQL con sistema de migraciones (estilo Django/Alembic)**
✔ ✅ **Docker deployment listo para Orange Pi 5 Plus**
✔ ✅ **Contador Oriental (IA local con Gemma 2:2b + Ollama)**
✔ ✅ **RAG con normativa uruguaya (IRPF, IVA, Inclusión Financiera, UI)**
✔ ✅ **Arquitectura async: AI no bloquea el event loop de Flet**
✔ ✅ **AIContext: Python pre-calcula todo, Gemma solo narra**
✔ ✅ **Detección de categorías con fuzzy matching y tokenización**
✔ ✅ **Chat premium: Markdown, chips, typing indicator animado**
✔ ✅ **Resumen de métodos de pago en contexto financiero**

**🎯 Sistema multi-familia con IA local funcional listo para producción!**

---

## ⚠️ Problemas Conocidos

### Evento correcto de Dropdown en Flet

**Aclaración importante**: El control `Dropdown` de Flet **NO tiene** el evento `on_change`. El evento correcto es **`on_select`**.

**Implementación correcta**:
```python
self.dropdown = ft.Dropdown(
    label="Seleccionar opción",
    options=[...]
)
self.dropdown.on_select = self._on_select_handler  # ✅ Correcto
```

**Solución implementada en este proyecto**:
- En `family_members_view.py`, se usa `dropdown.on_select` para detectar cuando el usuario selecciona un miembro
- Al seleccionar un miembro, se dispara automáticamente la carga de datos en el formulario
- No se requiere botón adicional, la carga es automática y transparente

**Patrón State + Sync**: Se implementó el patrón State + Sync profesional que centraliza el estado y sincroniza la UI de forma determinista. Este patrón es correcto, escalable y funciona perfectamente con `on_select`.

---

## 🤝 Contribuir

Si quieres contribuir al proyecto:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Implementa tu feature siguiendo la arquitectura MVC
4. Asegúrate de mantener el tipado estricto
5. Haz commit de tus cambios (`git commit -m 'Agregar nueva funcionalidad'`)
6. Push a la rama (`git push origin feature/nueva-funcionalidad`)
7. Abre un Pull Request

**Ideas para contribuir**: Revisa el [Roadmap de mejoras futuras](#-roadmap-de-mejoras-futuras) para ver funcionalidades pendientes.

---

## 📝 Licencia

Este proyecto está bajo licencia MIT - ver archivo LICENSE para más detalles.

---

## 🙏 Agradecimientos

* **Fleting Framework** - [alexyucra/Fleting](https://github.com/alexyucra/Fleting)
* **Flet** - Framework UI multiplataforma
* **SQLAlchemy** - ORM moderno para Python
* **Pydantic** - Validación de datos con tipado
