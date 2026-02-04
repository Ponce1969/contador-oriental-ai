# 🐳 Docker Deployment - Auditor Familiar

Guía completa para desplegar Auditor Familiar con Docker en Orange Pi 5 Plus (ARM64).

---

## 📋 Requisitos

### Orange Pi 5 Plus
- Docker 20.10+
- Docker Compose 2.0+
- 2GB RAM mínimo
- 10GB espacio en disco

### Instalación Docker en Orange Pi (ARM64)

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Agregar usuario al grupo docker
sudo usermod -aG docker $USER
newgrp docker

# Instalar Docker Compose
sudo apt install docker-compose-plugin

# Verificar instalación
docker --version
docker compose version
```

---

## 🚀 Despliegue Rápido

### 1. Clonar repositorio en Orange Pi

```bash
# SSH a tu Orange Pi
ssh usuario@ip-orange-pi

# Clonar proyecto
git clone <tu-repo-url> auditor-familiar
cd auditor-familiar
```

### 2. Configurar variables de entorno

```bash
# Copiar template
cp .env.example .env

# Editar con tus credenciales REALES
nano .env
```

**Variables OBLIGATORIAS a configurar:**

```bash
# PostgreSQL (CAMBIAR CONTRASEÑA)
POSTGRES_PASSWORD=tu_password_super_seguro_aqui

# Application (GENERAR SECRET_KEY)
SECRET_KEY=tu_secret_key_generado_aqui

# Opcional: pgAdmin
PGADMIN_PASSWORD=tu_password_pgadmin
```

**Generar SECRET_KEY seguro:**

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Iniciar servicios

```bash
# Construir y levantar servicios
docker compose up -d

# Ver logs
docker compose logs -f

# Verificar estado
docker compose ps
```

### 4. Ejecutar migraciones

```bash
# Primera vez - crear tablas
docker compose exec app python -m migrations.migrate

# Verificar tablas creadas
docker compose exec postgres psql -U auditor_user -d auditor_familiar -c "\dt"
```

### 5. Acceder a la aplicación

```bash
# Aplicación
http://ip-orange-pi:8550

# pgAdmin (opcional)
http://ip-orange-pi:5050
```

---

## 📁 Estructura de Servicios

```yaml
services:
  postgres:       # Base de datos PostgreSQL
  app:           # Aplicación Auditor Familiar
  pgadmin:       # Administrador BD (opcional)
```

### Volúmenes persistentes

```
postgres_data/  → Datos de PostgreSQL
app_data/       → Datos de la aplicación
pgadmin_data/   → Configuración pgAdmin
logs/           → Logs de la aplicación
backups/        → Backups de BD
```

---

## 🔧 Comandos Útiles

### Gestión de servicios

```bash
# Iniciar servicios
docker compose up -d

# Detener servicios
docker compose down

# Reiniciar servicios
docker compose restart

# Ver logs en tiempo real
docker compose logs -f app

# Ver logs de PostgreSQL
docker compose logs -f postgres

# Ejecutar comando en contenedor
docker compose exec app python -c "print('Hello')"
```

### Gestión de base de datos

```bash
# Backup de PostgreSQL
docker compose exec postgres pg_dump -U auditor_user auditor_familiar > backup_$(date +%Y%m%d).sql

# Restaurar backup
docker compose exec -T postgres psql -U auditor_user auditor_familiar < backup_20260203.sql

# Conectar a PostgreSQL
docker compose exec postgres psql -U auditor_user -d auditor_familiar

# Ver tablas
docker compose exec postgres psql -U auditor_user -d auditor_familiar -c "\dt"
```

### Mantenimiento

```bash
# Ver uso de espacio
docker system df

# Limpiar recursos no usados
docker system prune -a

# Ver logs de contenedor específico
docker logs auditor_familiar_app

# Reiniciar solo la app
docker compose restart app

# Reconstruir imagen
docker compose build --no-cache app
docker compose up -d app
```

---

## 🔒 Seguridad

### Variables de entorno

**⚠️ NUNCA subir `.env` a GitHub**

El archivo `.env` contiene:
- Contraseñas de PostgreSQL
- SECRET_KEY de la aplicación
- Credenciales de pgAdmin

Ya está protegido en `.gitignore`.

### Permisos de archivos

```bash
# Proteger .env
chmod 600 .env

# Solo el propietario puede leer/escribir
ls -la .env
# -rw------- 1 usuario usuario .env
```

### Firewall (opcional)

```bash
# Permitir solo puertos necesarios
sudo ufw allow 8550/tcp  # Aplicación
sudo ufw allow 5050/tcp  # pgAdmin (opcional)
sudo ufw enable
```

### Actualizar contraseñas

```bash
# Editar .env
nano .env

# Recrear servicios
docker compose down
docker compose up -d
```

---

## 📊 Monitoreo

### Ver estado de contenedores

```bash
# Estado general
docker compose ps

# Uso de recursos
docker stats

# Logs de errores
docker compose logs --tail=100 app | grep ERROR
```

### Health checks

```bash
# Verificar salud de PostgreSQL
docker compose exec postgres pg_isready -U auditor_user

# Verificar salud de la app
docker compose exec app python -c "import sys; sys.exit(0)"
```

---

## 🔄 Actualización de la aplicación

```bash
# 1. Hacer backup
docker compose exec postgres pg_dump -U auditor_user auditor_familiar > backup_pre_update.sql

# 2. Detener servicios
docker compose down

# 3. Actualizar código
git pull origin main

# 4. Reconstruir imagen
docker compose build --no-cache app

# 5. Iniciar servicios
docker compose up -d

# 6. Ejecutar migraciones (si hay)
docker compose exec app python -m migrations.migrate

# 7. Verificar logs
docker compose logs -f app
```

---

## 🐛 Troubleshooting

### Error: "POSTGRES_PASSWORD must be set"

```bash
# Verificar que .env existe y tiene la variable
cat .env | grep POSTGRES_PASSWORD

# Si no existe, agregarla
echo "POSTGRES_PASSWORD=tu_password" >> .env
```

### Error: "port is already allocated"

```bash
# Ver qué proceso usa el puerto
sudo netstat -tlnp | grep 8550

# Cambiar puerto en .env
echo "APP_PORT=8551" >> .env

# Reiniciar
docker compose down && docker compose up -d
```

### Error: "no space left on device"

```bash
# Limpiar imágenes no usadas
docker system prune -a

# Ver uso de disco
df -h
docker system df
```

### PostgreSQL no inicia

```bash
# Ver logs
docker compose logs postgres

# Verificar permisos de volumen
docker volume inspect auditor-familiar_postgres_data

# Recrear volumen (CUIDADO: borra datos)
docker compose down -v
docker compose up -d
```

### App no se conecta a PostgreSQL

```bash
# Verificar que postgres esté healthy
docker compose ps

# Verificar variables de entorno
docker compose exec app env | grep POSTGRES

# Verificar conectividad
docker compose exec app ping postgres
```

---

## 📦 Backup Automático

### Script de backup diario

```bash
# Crear script
cat > /home/usuario/backup-auditor.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/usuario/auditor-familiar/backups"
cd /home/usuario/auditor-familiar

# Backup de PostgreSQL
docker compose exec -T postgres pg_dump -U auditor_user auditor_familiar > "$BACKUP_DIR/db_$DATE.sql"

# Comprimir
gzip "$BACKUP_DIR/db_$DATE.sql"

# Mantener solo últimos 7 días
find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime +7 -delete

echo "Backup completado: db_$DATE.sql.gz"
EOF

# Dar permisos
chmod +x /home/usuario/backup-auditor.sh

# Agregar a cron (diario a las 2am)
crontab -e
# Agregar línea:
0 2 * * * /home/usuario/backup-auditor.sh >> /home/usuario/backup.log 2>&1
```

---

## 🌐 Acceso Remoto

### Configurar dominio (opcional)

```bash
# Instalar Nginx como reverse proxy
sudo apt install nginx

# Configurar
sudo nano /etc/nginx/sites-available/auditor-familiar

# Contenido:
server {
    listen 80;
    server_name auditor.tu-dominio.com;

    location / {
        proxy_pass http://localhost:8550;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# Habilitar
sudo ln -s /etc/nginx/sites-available/auditor-familiar /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### SSL con Let's Encrypt (opcional)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d auditor.tu-dominio.com
```

---

## 📚 Referencias

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- [PostgreSQL Docker](https://hub.docker.com/_/postgres)
- [Orange Pi Documentation](http://www.orangepi.org/)

---

## 🆘 Soporte

Si encuentras problemas:

1. Revisar logs: `docker compose logs -f`
2. Verificar estado: `docker compose ps`
3. Verificar variables: `cat .env`
4. Revisar esta guía de troubleshooting
