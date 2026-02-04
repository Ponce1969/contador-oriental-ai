# � Auditor Familiar de Gastos e Ingresos

Aplicación de escritorio construida con **Python 3.12**, **Flet**, **Fleting** y **arquitectura MVC** para gestión completa de finanzas familiares.

Sistema profesional de seguimiento de ingresos y gastos con balance automático, diseñado siguiendo **buenas prácticas profesionales**, con tipado estricto, separación de responsabilidades y manejo explícito de errores mediante `Result[T, E]`.

**🚀 Basado en Fleting Framework** - Micro framework MVC para Flet con routing automático, layouts consistentes y CLI productiva.

---

## 🎯 Objetivo del proyecto

Sistema completo de gestión financiera familiar que permite:

### **Funcionalidades Implementadas** ✅

* **👥 Gestión de Familia**: Registrar miembros con tipos de ingreso (Sueldo fijo, Jornalero, Mixto, Sin ingresos)
* **💰 Gestión de Ingresos**: Registrar ingresos diarios (jornaleros) o mensuales (sueldos fijos) con 9 categorías
* **💸 Gestión de Gastos**: Registrar gastos familiares con categorías, subcategorías y métodos de pago
* **📊 Dashboard**: Balance automático mensual (Ingresos - Gastos) con indicadores visuales
* **✏️ Edición completa**: Editar y eliminar todos los registros
* **🇺🇾 Formato uruguayo**: Montos con separador de miles ($50.000)
* **📈 Resúmenes**: Análisis por categorías con barras de progreso y porcentajes

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

- Cada familia tiene su propio `familia_id`
- Todas las queries filtran automáticamente por familia
- Los usuarios solo ven datos de su familia
- Aislamiento en: `usuarios`, `family_members`, `incomes`, `expenses`

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

## � Instalación y Uso

### **Requisitos previos**

* Python 3.12+
* uv (gestor de paquetes)

### **Instalación**

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
uv run python -m migrations.migrate

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

1. **Registra tu familia** en 👥 Familia
   - Agrega miembros con su tipo de ingreso
   - Para sueldos fijos, indica el monto mensual

2. **Registra ingresos** en 💰 Ingresos
   - Jornaleros: registra cada día trabajado
   - Sueldos fijos: registra cuando cobras
   - Extras: bonos, freelance, etc.

3. **Registra gastos** en 💸 Gastos
   - Selecciona categoría y subcategoría
   - Indica método de pago
   - Marca si es recurrente

4. **Consulta el balance** en 📊 Dashboard
   - Ve el balance del mes actual
   - Analiza ingresos vs gastos
   - Identifica categorías con mayor gasto

---

## 🛣️ Roadmap de mejoras futuras

### **Funcionalidades pendientes** 🔮

* **📅 Selector de mes/año**: Ver balance de meses anteriores
* **📊 Gráficos avanzados**: Gráficos de línea, torta, evolución mensual
* **🔔 Alertas**: Notificaciones cuando gastos superan presupuesto
* **💾 Exportar datos**: Exportar a Excel/CSV para análisis externo
* **🎯 Presupuestos**: Definir presupuestos por categoría
* **📱 Versión móvil**: Adaptar para Android/iOS con Flet
* **👨‍👩‍👧‍👦 Multi-usuario**: Login y datos por familia
* **🔄 Sincronización**: Sync entre dispositivos (cloud)
* **📈 Proyecciones**: Predicción de gastos futuros con IA
* **🏦 Integración bancaria**: Importar movimientos automáticamente
* **📸 Recibos**: Adjuntar fotos de tickets/facturas
* **🔍 Búsqueda avanzada**: Filtros por fecha, monto, categoría
* **📊 Comparativas**: Comparar meses/años anteriores
* **💡 Recomendaciones**: Sugerencias de ahorro basadas en patrones

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

✔ ✅ **Sistema completo de gestión familiar implementado**
✔ ✅ **Módulo de Familia con edición**
✔ ✅ **Módulo de Ingresos con 9 categorías**
✔ ✅ **Módulo de Gastos con categorías y subcategorías**
✔ ✅ **Dashboard con balance automático mensual**
✔ ✅ **Formato uruguayo con separador de miles**
✔ ✅ **Arquitectura MVC con tipado estricto**
✔ ✅ **Base de datos SQLite con SQLAlchemy 2.0**

**🎯 Sistema funcional listo para producción!**

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
