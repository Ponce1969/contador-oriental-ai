#!/bin/sh
set -e

echo "🎙️ [VOICE] Starting Voice API on port 8553..."
exec python -m uvicorn voice_api.main:app --host 0.0.0.0 --port 8553
