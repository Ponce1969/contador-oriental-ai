# 📁 Estructura del Proyecto

Auditor Familiar - Sistema de gestión de finanzas familiares con Flet

---

## 🗂️ Organización de Carpetas

```
flet/
├── 📄 main.py                      # Punto de entrada de la aplicación
├── 📄 pyproject.toml               # Configuración del proyecto (uv)
├── 📄 README.md                    # Documentación principal
├── 📄 COLORES_GUIA.md             # Guía de paleta de colores
├── 📄 ESTRUCTURA.md               # Este archivo
│
├── 📁 assets/                      # Recursos estáticos
│   ├── icon-gastos.png            # Icono original (PNG)
│   └── icon-gastos.ico            # Icono para Windows (ICO)
│
├── 📁 configs/                     # Configuraciones
│   ├── app_config.py              # Configuración general
│   ├── database_config.py         # Configuración de BD (SQLite/PostgreSQL)
│   └── routes.py                  # Rutas de la aplicación
│
├── 📁 core/                        # Núcleo del framework
│   ├── database.py                # Utilidades de BD
│   ├── error_handler.py           # Manejo de errores
│   ├── i18n.py                    # Internacionalización
│   ├── logger.py                  # Sistema de logs
│   ├── router.py                  # Router de navegación
│   └── sqlalchemy_session.py      # Sesiones de SQLAlchemy
│
├── 📁 database/                    # Capa de base de datos
│   ├── base.py                    # Base declarativa
│   ├── engine.py                  # Motor de SQLAlchemy
│   └── tables.py                  # Definición de tablas
│
├── 📁 models/                      # Modelos de dominio (Pydantic)
│   ├── categories.py              # Categorías y enums
│   ├── errors.py                  # Errores de dominio
│   ├── expense_model.py           # Modelo de gastos
│   ├── family_member_model.py     # Modelo de miembros
│   └── income_model.py            # Modelo de ingresos
│
├── 📁 controllers/                 # Controladores MVC
│   ├── expense_controller.py      # Controller de gastos
│   ├── family_member_controller.py # Controller de familia
│   └── income_controller.py       # Controller de ingresos
│
├── 📁 services/                    # Lógica de negocio
│   ├── expense_service.py         # Servicio de gastos
│   ├── family_member_service.py   # Servicio de familia
│   └── income_service.py          # Servicio de ingresos
│
├── 📁 repositories/                # Capa de persistencia
│   ├── expense_repository.py      # Repositorio de gastos
│   ├── family_member_mappers.py   # Mappers familia
│   ├── family_member_repository.py # Repositorio familia
│   ├── income_mappers.py          # Mappers ingresos
│   ├── income_repository.py       # Repositorio ingresos
│   └── mappers.py                 # Mappers generales
│
├── 📁 views/                       # Vistas (UI)
│   ├── layouts/
│   │   └── main_layout.py         # Layout principal
│   └── pages/
│       ├── dashboard_view.py      # Dashboard principal
│       ├── expenses_view.py       # Vista de gastos
│       ├── family_members_view.py # Vista de familia
│       ├── home_view.py           # Página de inicio
│       ├── incomes_view.py        # Vista de ingresos
│       └── settings_view.py       # Configuraciones
│
├── 📁 migrations/                  # Sistema de migraciones
│   ├── __init__.py
│   ├── migrate.py                 # Script principal
│   ├── README.md                  # Documentación
│   └── 001_initial.py             # Migración inicial
│
├── 📁 scripts/                     # Scripts de utilidad
│   ├── README.md                  # Documentación
│   └── convert_icon.py            # Convertir PNG a ICO
│
├── 📁 logs/                        # Archivos de log
│   └── fleting.log                # Log principal
│
└── 📁 .venv/                       # Entorno virtual (ignorado)
```

---

## 🎯 Arquitectura MVC

### **Model (Modelos de Dominio)**
- Pydantic para validación
- No conocen la UI ni la BD
- Representan conceptos del negocio

### **View (Vistas)**
- Flet UI components
- Solo presentación
- No contienen lógica de negocio

### **Controller (Controladores)**
- Orquestan Model y View
- Manejan sesiones de BD
- Delegan lógica a Services

### **Service (Servicios)**
- Lógica de negocio
- Validaciones
- Retornan `Result[T, E]`

### **Repository (Repositorios)**
- Acceso a datos
- Mappers ORM ↔ Dominio
- Aíslan SQLAlchemy

---

## 🗄️ Base de Datos

### **Actual: SQLite** (desarrollo)
- Archivo: `shopping.db`
- Ideal para desarrollo local
- Sin configuración adicional

### **Futuro: PostgreSQL** (producción)
- Configuración en `configs/database_config.py`
- Cambiar `DB_TYPE = "postgresql"`
- Ejecutar migraciones

### **Sistema de Migraciones**
- Inspirado en Django
- Comandos: `migrate`, `rollback`, `status`
- Migraciones numeradas (001, 002, 003...)

---

## 🎨 Recursos Visuales

### **Colores**
- Guía completa en `COLORES_GUIA.md`
- Paleta suave y profesional
- Dashboard: Azul/Cyan
- Familia: Morado
- Ingresos: Cyan/Teal
- Gastos: Naranja

### **Iconos**
- `assets/icon-gastos.png` - Original
- `assets/icon-gastos.ico` - Para Windows

---

## 🚀 Comandos Útiles

### **Desarrollo**
```bash
# Ejecutar aplicación
uv run python main.py

# Ejecutar migraciones
python migrations/migrate.py migrate

# Ver estado de migraciones
python migrations/migrate.py status
```

### **Utilidades**
```bash
# Convertir icono
python scripts/convert_icon.py
```

---

## 📦 Dependencias Principales

- **flet**: Framework UI
- **sqlalchemy**: ORM
- **pydantic**: Validación de datos
- **psycopg2-binary**: Driver PostgreSQL
- **Pillow**: Procesamiento de imágenes

---

## 🔄 Flujo de Datos

```
Usuario → View → Controller → Service → Repository → Database
                                ↓
                            Validación
                                ↓
                          Result[T, E]
```

---

## 📝 Convenciones

### **Nombres de Archivos**
- Controllers: `*_controller.py`
- Services: `*_service.py`
- Repositories: `*_repository.py`
- Views: `*_view.py`
- Models: `*_model.py`

### **Migraciones**
- Formato: `00X_descripcion.py`
- Funciones: `up(db)` y `down(db)`
- Usar `text()` para SQL raw

---

## 🎯 Estado Actual

✅ Sistema completo de gestión familiar  
✅ Dashboard con balance automático  
✅ Formato uruguayo ($50.000)  
✅ Sistema de migraciones  
✅ Soporte PostgreSQL listo  
✅ Colores alegres y profesionales  
✅ Banner de bienvenida  

---

## 🔮 Próximas Mejoras

- Multi-usuarios con login
- Selector de mes/año en Dashboard
- Gráficos avanzados
- Exportar a Excel/CSV
- Versión móvil (Android/iOS)
- Versión web
