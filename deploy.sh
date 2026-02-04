#!/bin/bash
# Script de despliegue para Auditor Familiar en Orange Pi 5 Plus

set -e

echo "🚀 Auditor Familiar - Deployment Script"
echo "========================================"
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verificar Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker no está instalado${NC}"
    echo "Instalar con: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# Verificar Docker Compose
if ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose no está instalado${NC}"
    echo "Instalar con: sudo apt install docker-compose-plugin"
    exit 1
fi

echo -e "${GREEN}✅ Docker y Docker Compose detectados${NC}"
echo ""

# Verificar .env
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  Archivo .env no encontrado${NC}"
    echo "Copiando .env.example a .env..."
    cp .env.example .env
    echo ""
    echo -e "${YELLOW}⚠️  IMPORTANTE: Edita .env con tus credenciales reales${NC}"
    echo "Variables obligatorias:"
    echo "  - POSTGRES_PASSWORD"
    echo "  - SECRET_KEY"
    echo ""
    read -p "¿Deseas editar .env ahora? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ${EDITOR:-nano} .env
    else
        echo -e "${RED}❌ Debes configurar .env antes de continuar${NC}"
        exit 1
    fi
fi

# Verificar variables obligatorias
source .env
if [ -z "$POSTGRES_PASSWORD" ] || [ "$POSTGRES_PASSWORD" = "your_secure_password_here" ]; then
    echo -e "${RED}❌ POSTGRES_PASSWORD no configurado en .env${NC}"
    exit 1
fi

if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "change_this_to_a_random_secret_key" ]; then
    echo -e "${RED}❌ SECRET_KEY no configurado en .env${NC}"
    echo "Generar con: python3 -c \"import secrets; print(secrets.token_hex(32))\""
    exit 1
fi

echo -e "${GREEN}✅ Variables de entorno configuradas${NC}"
echo ""

# Crear directorios necesarios
echo "📁 Creando directorios..."
mkdir -p logs backups
echo -e "${GREEN}✅ Directorios creados${NC}"
echo ""

# Construir imágenes
echo "🔨 Construyendo imágenes Docker..."
docker compose build --no-cache
echo -e "${GREEN}✅ Imágenes construidas${NC}"
echo ""

# Iniciar servicios
echo "🚀 Iniciando servicios..."
docker compose up -d
echo -e "${GREEN}✅ Servicios iniciados${NC}"
echo ""

# Esperar a que PostgreSQL esté listo
echo "⏳ Esperando a PostgreSQL..."
sleep 10

# Verificar salud de PostgreSQL
if docker compose exec postgres pg_isready -U ${POSTGRES_USER:-auditor_user} > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL está listo${NC}"
else
    echo -e "${RED}❌ PostgreSQL no está respondiendo${NC}"
    echo "Ver logs: docker compose logs postgres"
    exit 1
fi
echo ""

# Ejecutar migraciones
echo "🔄 Ejecutando migraciones..."
if docker compose exec app python -m migrations.migrate; then
    echo -e "${GREEN}✅ Migraciones completadas${NC}"
else
    echo -e "${YELLOW}⚠️  Error en migraciones (puede ser normal si ya existen)${NC}"
fi
echo ""

# Mostrar estado
echo "📊 Estado de servicios:"
docker compose ps
echo ""

# Información de acceso
echo "=========================================="
echo -e "${GREEN}✅ Despliegue completado exitosamente${NC}"
echo "=========================================="
echo ""
echo "🌐 Acceso a la aplicación:"
echo "   http://$(hostname -I | awk '{print $1}'):${APP_PORT:-8550}"
echo ""
echo "🗄️  PostgreSQL:"
echo "   Host: localhost"
echo "   Port: ${POSTGRES_PORT:-5432}"
echo "   Database: ${POSTGRES_DB:-auditor_familiar}"
echo "   User: ${POSTGRES_USER:-auditor_user}"
echo ""
echo "📊 pgAdmin (opcional):"
echo "   http://$(hostname -I | awk '{print $1}'):${PGADMIN_PORT:-5050}"
echo "   Email: ${PGADMIN_EMAIL:-admin@auditor.local}"
echo ""
echo "📝 Comandos útiles:"
echo "   Ver logs:        docker compose logs -f"
echo "   Detener:         docker compose down"
echo "   Reiniciar:       docker compose restart"
echo "   Backup DB:       docker compose exec postgres pg_dump -U ${POSTGRES_USER:-auditor_user} ${POSTGRES_DB:-auditor_familiar} > backup.sql"
echo ""
echo "📖 Ver docs/DOCKER_DEPLOYMENT.md para más información"
echo ""
