# PostgreSQL Setup - Auditor Familiar

Guía para configurar PostgreSQL en producción con aislamiento multi-tenant.

---

## 🔐 Seguridad Multi-Tenant

La aplicación está diseñada para **múltiples familias** con aislamiento completo:

- Cada familia tiene su propio `familia_id`
- Los usuarios solo ven datos de su familia
- Todas las queries filtran por `familia_id`
- Tablas con aislamiento: `usuarios`, `family_members`, `incomes`, `expenses`

---

## 📋 Requisitos

- PostgreSQL 14+ instalado
- Python 3.12+
- Acceso a crear bases de datos

---

## 🚀 Instalación PostgreSQL

### Windows

```bash
# Descargar desde https://www.postgresql.org/download/windows/
# O usar Chocolatey
choco install postgresql

# Iniciar servicio
net start postgresql-x64-14
```

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### macOS

```bash
brew install postgresql@14
brew services start postgresql@14
```

---

## ⚙️ Configuración Base de Datos

### 1. Crear Base de Datos

```bash
# Conectar como postgres
sudo -u postgres psql

# Crear base de datos
CREATE DATABASE auditor_familiar;

# Crear usuario
CREATE USER auditor_user WITH PASSWORD 'tu_password_seguro';

# Dar permisos
GRANT ALL PRIVILEGES ON DATABASE auditor_familiar TO auditor_user;

# Salir
\q
```

### 2. Configurar Variables de Entorno

Copiar `.env.example` a `.env`:

```bash
cp .env.example .env
```

Editar `.env` con tus credenciales:

```bash
# Database Configuration
DB_TYPE=postgresql

# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=auditor_familiar
POSTGRES_USER=auditor_user
POSTGRES_PASSWORD=tu_password_seguro
```

**⚠️ IMPORTANTE:** Nunca subir `.env` a GitHub. Ya está en `.gitignore`.

---

## 🔄 Ejecutar Migraciones

```bash
# Ejecutar migraciones
uv run python -m migrations.migrate

# Verificar tablas creadas
psql -U auditor_user -d auditor_familiar -c "\dt"
```

Deberías ver:

```
 Schema |      Name       | Type  |     Owner
--------+-----------------+-------+---------------
 public | expenses        | table | auditor_user
 public | familias        | table | auditor_user
 public | family_members  | table | auditor_user
 public | incomes         | table | auditor_user
 public | usuarios        | table | auditor_user
```

---

## 🧪 Verificar Conexión

```bash
# Crear script de prueba
cat > test_connection.py << 'EOF'
from configs.database_config import DatabaseConfig
from database.engine import engine

print(f"Database URL: {DatabaseConfig.get_database_url()}")
print(f"Using PostgreSQL: {DatabaseConfig.is_postgresql()}")

try:
    with engine.connect() as conn:
        result = conn.execute("SELECT version()")
        print(f"✅ Connected: {result.fetchone()[0]}")
except Exception as e:
    print(f"❌ Error: {e}")
EOF

# Ejecutar
uv run python test_connection.py
```

---

## 🏗️ Esquema Multi-Tenant

```sql
-- Tabla de familias (tenant principal)
CREATE TABLE familias (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tabla de usuarios (por familia)
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    familia_id INTEGER NOT NULL REFERENCES familias(id),
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    nombre_completo VARCHAR(200),
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

-- Todas las demás tablas tienen familia_id
-- Ejemplo: expenses, incomes, family_members
```

---

## 🔒 Seguridad en Producción

### Variables de Entorno

```bash
# Generar SECRET_KEY seguro
python -c "import secrets; print(secrets.token_hex(32))"

# Agregar a .env
SECRET_KEY=<resultado_del_comando>
```

### Permisos PostgreSQL

```sql
-- Revocar acceso público
REVOKE ALL ON DATABASE auditor_familiar FROM PUBLIC;

-- Solo el usuario de la app
GRANT CONNECT ON DATABASE auditor_familiar TO auditor_user;
GRANT ALL ON ALL TABLES IN SCHEMA public TO auditor_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO auditor_user;
```

### Backup Automático

```bash
# Crear script de backup
cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -U auditor_user auditor_familiar > backup_$DATE.sql
EOF

chmod +x backup.sh

# Agregar a cron (diario a las 2am)
0 2 * * * /path/to/backup.sh
```

---

## 🐛 Troubleshooting

### Error: "password authentication failed"

```bash
# Editar pg_hba.conf
sudo nano /etc/postgresql/14/main/pg_hba.conf

# Cambiar de 'peer' a 'md5'
local   all   all   md5

# Reiniciar
sudo systemctl restart postgresql
```

### Error: "database does not exist"

```bash
# Crear manualmente
createdb -U postgres auditor_familiar
```

### Error: "connection refused"

```bash
# Verificar que PostgreSQL esté corriendo
sudo systemctl status postgresql

# Verificar puerto
sudo netstat -tlnp | grep 5432
```

---

## 📊 Monitoreo

### Ver Conexiones Activas

```sql
SELECT * FROM pg_stat_activity 
WHERE datname = 'auditor_familiar';
```

### Ver Tamaño de Tablas

```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## 🔄 Migrar de SQLite a PostgreSQL

```bash
# 1. Exportar datos de SQLite
sqlite3 shopping.db .dump > sqlite_dump.sql

# 2. Convertir sintaxis (manual o con herramientas)
# SQLite usa AUTOINCREMENT, PostgreSQL usa SERIAL
# SQLite usa DATETIME, PostgreSQL usa TIMESTAMP

# 3. Importar a PostgreSQL
psql -U auditor_user -d auditor_familiar < converted_dump.sql
```

---

## 📚 Referencias

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQLAlchemy PostgreSQL Dialect](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html)
- [Argon2 Password Hashing](https://argon2-cffi.readthedocs.io/)
