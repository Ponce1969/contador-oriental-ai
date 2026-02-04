# 🔍 Verificar Puertos Libres en Orange Pi

Guía rápida para verificar qué puertos están disponibles antes de desplegar.

---

## 📋 Puertos que usa Auditor Familiar

| Servicio | Puerto por defecto | Variable en .env |
|----------|-------------------|------------------|
| PostgreSQL | 5432 | `POSTGRES_PORT` |
| Aplicación | 8550 | `APP_PORT` |
| pgAdmin | 5050 | `PGADMIN_PORT` |

---

## 🔍 Comandos para verificar puertos

### Opción 1: Ver todos los puertos en uso

```bash
# Ver todos los puertos TCP en uso
sudo netstat -tlnp

# O con ss (más moderno)
sudo ss -tlnp
```

### Opción 2: Verificar puerto específico

```bash
# Verificar si puerto 5432 está en uso
sudo netstat -tlnp | grep :5432

# Verificar si puerto 8550 está en uso
sudo netstat -tlnp | grep :8550

# Verificar si puerto 5050 está en uso
sudo netstat -tlnp | grep :5050
```

### Opción 3: Ver contenedores Docker y sus puertos

```bash
# Ver todos los contenedores corriendo
docker ps

# Ver puertos de contenedores
docker ps --format "table {{.Names}}\t{{.Ports}}"

# Ver solo puertos PostgreSQL
docker ps | grep postgres
```

---

## 🔧 Cambiar puertos si están ocupados

### 1. Editar .env

```bash
cd auditor-familiar
nano .env
```

### 2. Cambiar puertos ocupados

**Si PostgreSQL 5432 está ocupado:**
```bash
POSTGRES_PORT=5433  # O 5434, 5435, etc.
```

**Si App 8550 está ocupado:**
```bash
APP_PORT=8551  # O 8552, 8553, etc.
```

**Si pgAdmin 5050 está ocupado:**
```bash
PGADMIN_PORT=5051  # O 5052, 5053, etc.
```

### 3. Guardar y salir

```bash
# Ctrl+O para guardar
# Ctrl+X para salir
```

---

## 📝 Ejemplo de configuración .env

```bash
# ==============================================
# AUDITOR FAMILIAR - Environment Variables
# ==============================================

# ---------------------------------------------
# Database Configuration
# ---------------------------------------------
DB_TYPE=postgresql

# PostgreSQL - CAMBIAR PUERTO SI ESTÁ OCUPADO
POSTGRES_HOST=localhost
POSTGRES_PORT=5433  # ← Cambiado de 5432 a 5433
POSTGRES_DB=auditor_familiar
POSTGRES_USER=auditor_user
POSTGRES_PASSWORD=mi_password_super_seguro_123

# ---------------------------------------------
# Application Configuration
# ---------------------------------------------
APP_ENV=production

# SECRET_KEY - GENERAR UNO NUEVO
SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6

# ---------------------------------------------
# Security
# ---------------------------------------------
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,ip-orange-pi

# ---------------------------------------------
# Logging
# ---------------------------------------------
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# ---------------------------------------------
# Docker Configuration
# ---------------------------------------------
APP_PORT=8551  # ← Cambiado de 8550 a 8551

# pgAdmin (opcional)
PGADMIN_EMAIL=admin@auditor.local
PGADMIN_PASSWORD=mi_password_pgadmin_123
PGADMIN_PORT=5051  # ← Cambiado de 5050 a 5051
```

---

## 🚀 Después de cambiar puertos

### 1. Verificar que .env está correcto

```bash
cat .env | grep PORT
```

Deberías ver:
```
POSTGRES_PORT=5433
APP_PORT=8551
PGADMIN_PORT=5051
```

### 2. Iniciar servicios

```bash
./deploy.sh
```

O manualmente:
```bash
docker compose up -d
```

### 3. Verificar que levantaron correctamente

```bash
# Ver estado
docker compose ps

# Ver logs
docker compose logs -f
```

### 4. Acceder a la aplicación

```bash
# Con el nuevo puerto
http://ip-orange-pi:8551  # En lugar de 8550
```

---

## 🐛 Troubleshooting

### Error: "port is already allocated"

```bash
# 1. Ver qué proceso usa el puerto
sudo netstat -tlnp | grep :8550

# 2. Si es un contenedor Docker
docker ps | grep 8550

# 3. Cambiar puerto en .env
nano .env
# Cambiar APP_PORT=8551

# 4. Reiniciar
docker compose down
docker compose up -d
```

### Error: "address already in use"

```bash
# Ver todos los puertos en uso
sudo netstat -tlnp

# Elegir puertos libres y actualizar .env
nano .env
```

---

## 💡 Consejos

1. **Usa puertos altos** (8000+) para evitar conflictos
2. **Documenta tus puertos** en un archivo para recordarlos
3. **Verifica antes de desplegar** con `netstat` o `ss`
4. **Usa rangos** (ej: 8550-8559 para tus apps)

---

## 📊 Ejemplo de organización de puertos

```
PostgreSQL containers:
- proyecto1: 5432
- proyecto2: 5433
- auditor-familiar: 5434  ← Tu nuevo puerto

Web apps:
- proyecto1: 8080
- proyecto2: 8090
- auditor-familiar: 8550  ← Si está libre

pgAdmin instances:
- general: 5050
- auditor-familiar: 5051  ← Si 5050 está ocupado
```

---

## 🔗 Referencias

- [Netstat documentation](https://linux.die.net/man/8/netstat)
- [Docker port mapping](https://docs.docker.com/config/containers/container-networking/)
