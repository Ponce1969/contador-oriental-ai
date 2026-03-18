#!/bin/sh
set -e

echo "⏳ Esperando que PostgreSQL esté listo..."
until python -c "
import psycopg2, os, sys
try:
    psycopg2.connect(
        host=os.getenv('POSTGRES_HOST','postgres'),
        port=os.getenv('POSTGRES_PORT','5432'),
        dbname=os.getenv('POSTGRES_DB','auditor_familiar'),
        user=os.getenv('POSTGRES_USER','auditor_user'),
        password=os.getenv('POSTGRES_PASSWORD',''),
    ).close()
except Exception as e:
    sys.exit(1)
"; do
  echo "  PostgreSQL no disponible todavía, reintentando..."
  sleep 2
done

echo "✅ PostgreSQL listo."
echo "🔄 Aplicando migraciones..."
python -m fleting db migrate
echo "✅ Migraciones aplicadas."
echo "🚀 Iniciando aplicación..."
exec python main.py
