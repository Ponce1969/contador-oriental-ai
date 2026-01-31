# 🗄️ Sistema de Migraciones de Base de Datos

Sistema de migraciones inspirado en Django y Alembic para gestionar cambios en el esquema de la base de datos.

---

## 📋 Comandos Disponibles

### **Ejecutar migraciones pendientes**
```bash
python migrations/migrate.py migrate
```

### **Revertir última migración**
```bash
python migrations/migrate.py rollback
```

### **Ver estado de migraciones**
```bash
python migrations/migrate.py status
```

---

## 📁 Estructura de Migraciones

```
migrations/
├── __init__.py
├── migrate.py              # Script principal de migraciones
├── README.md              # Esta documentación
├── 001_initial.py         # Migración inicial
├── 002_nombre.py          # Segunda migración
└── 003_nombre.py          # Tercera migración
```

---

## ✍️ Crear una Nueva Migración

### **Paso 1: Crear archivo numerado**

Crear archivo `migrations/00X_descripcion.py` con el siguiente formato:

```python
"""
Descripción de la migración
"""

def up(db):
    """Aplicar cambios a la base de datos"""
    db.execute("""
        ALTER TABLE tabla ADD COLUMN nueva_columna TEXT;
    """)
    print("✅ Cambios aplicados")

def down(db):
    """Revertir cambios (rollback)"""
    db.execute("""
        ALTER TABLE tabla DROP COLUMN nueva_columna;
    """)
    print("↩️ Cambios revertidos")
```

### **Paso 2: Ejecutar migración**

```bash
python migrations/migrate.py migrate
```

---

## 🔄 Cambiar de SQLite a PostgreSQL

### **Paso 1: Instalar dependencias**

```bash
uv pip install psycopg2-binary
```

### **Paso 2: Configurar PostgreSQL**

Editar `configs/database_config.py`:

```python
class DatabaseConfig:
    # Cambiar a "postgresql"
    DB_TYPE: DatabaseType = "postgresql"
    
    # Configurar credenciales
    POSTGRES_HOST = "localhost"
    POSTGRES_PORT = "5432"
    POSTGRES_DB = "auditor_familiar"
    POSTGRES_USER = "postgres"
    POSTGRES_PASSWORD = "tu_password"
```

### **Paso 3: Crear base de datos en PostgreSQL**

```sql
CREATE DATABASE auditor_familiar;
```

### **Paso 4: Ejecutar migraciones**

```bash
python migrations/migrate.py migrate
```

---

## 🎯 Buenas Prácticas

### ✅ **Hacer:**
- Numerar migraciones secuencialmente (001, 002, 003...)
- Escribir descripciones claras en los nombres
- Implementar siempre `up()` y `down()`
- Probar migraciones antes de commitear
- Versionar migraciones junto al código

### ❌ **No hacer:**
- Editar migraciones ya aplicadas
- Saltar números en la secuencia
- Dejar `down()` vacío sin razón
- Hacer cambios destructivos sin backup

---

## 📊 Ejemplo de Flujo de Trabajo

### **Desarrollo local (SQLite)**

```bash
# 1. Crear nueva migración
# Crear archivo: migrations/002_add_email_to_users.py

# 2. Ver estado
python migrations/migrate.py status

# 3. Aplicar migración
python migrations/migrate.py migrate

# 4. Si hay error, revertir
python migrations/migrate.py rollback
```

### **Producción (PostgreSQL)**

```bash
# 1. Cambiar configuración a PostgreSQL
# Editar configs/database_config.py

# 2. Ejecutar migraciones
python migrations/migrate.py migrate

# 3. Verificar estado
python migrations/migrate.py status
```

---

## 🔍 Tabla de Control de Migraciones

El sistema crea automáticamente la tabla `_fleting_migrations`:

```sql
CREATE TABLE _fleting_migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_name TEXT NOT NULL UNIQUE,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Esta tabla registra qué migraciones ya fueron aplicadas.

---

## 🚀 Ventajas del Sistema

- ✅ **Versionado**: Cada cambio de esquema queda registrado
- ✅ **Reproducible**: Otros desarrolladores pueden aplicar las mismas migraciones
- ✅ **Reversible**: Rollback con `down()`
- ✅ **Multiplataforma**: Funciona con SQLite y PostgreSQL
- ✅ **Simple**: Sin dependencias externas complejas

---

## 📝 Notas Importantes

### **SQLite vs PostgreSQL**

- **SQLite**: Limitaciones en `ALTER TABLE` (no puede eliminar columnas fácilmente)
- **PostgreSQL**: Soporte completo de DDL, mejor para producción

### **Variables de Entorno**

Puedes usar variables de entorno para configuración:

```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=auditor_familiar
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=secret
```

---

## 🆘 Solución de Problemas

### **Error: "Migration already applied"**

La migración ya fue ejecutada. Verificar con:
```bash
python migrations/migrate.py status
```

### **Error: "Connection refused"**

PostgreSQL no está corriendo o credenciales incorrectas.

### **Error en rollback**

SQLite tiene limitaciones. Considera recrear la BD en desarrollo.

---

## 📚 Referencias

- [Django Migrations](https://docs.djangoproject.com/en/stable/topics/migrations/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Core](https://docs.sqlalchemy.org/en/20/core/)
