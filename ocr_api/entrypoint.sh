#!/bin/sh
set -e

echo "🚀 [OCR] Starting OCR API on port 8551..."
exec python -m uvicorn ocr_api.main:app --host 0.0.0.0 --port 8551
