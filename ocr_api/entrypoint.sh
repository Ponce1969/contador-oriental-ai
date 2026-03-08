#!/bin/sh
set -e

echo "⏳ [OCR] Esperando que PostgreSQL esté listo..."
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
except Exception:
    sys.exit(1)
"; do
  echo "  [OCR] PostgreSQL no disponible todavía, reintentando..."
  sleep 2
done

echo "✅ [OCR] PostgreSQL listo."
echo "🚀 [OCR] Iniciando OCR API..."
exec python -m uvicorn ocr_api.main:app --host 0.0.0.0 --port 8551
