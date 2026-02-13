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
└── flet_types/                       # Tipos correctos Flet
    └── flet_types.py
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

---

## 🛣️ Roadmap de mejoras futuras

### **Funcionalidades pendientes** 🔮

* **🤖 AI Contador Uruguayo**: Asistente con Ollama (Gemma2:2b) + RAG curado
  - 9 archivos MD con normativa uruguaya (IRPF, IVA, Ley de Inclusión Financiera, UI)
  - Análisis contextual de gastos familiares
  - Recomendaciones fiscales personalizadas
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

**🎯 Sistema multi-familia funcional listo para producción!**

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
