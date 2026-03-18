# Dockerfile para Auditor Familiar
# Optimizado para Orange Pi 5 Plus (ARM64)

FROM python:3.12-slim

# Metadata
LABEL maintainer="tu-email@example.com"
LABEL description="Auditor Familiar - Sistema de gestión de finanzas familiares"
LABEL version="1.0.0"

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/app/.venv/bin:/home/appuser/.local/bin:${PATH}" \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# Instalar dependencias del sistema (incluyendo Tesseract OCR para tickets)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    tesseract-ocr \
    tesseract-ocr-spa \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar uv globalmente
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Crear usuario no-root para seguridad
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /app/logs && \
    chown -R appuser:appuser /app

# Establecer directorio de trabajo
WORKDIR /app

# Copiar archivos de dependencias
COPY --chown=appuser:appuser pyproject.toml ./

# Instalar dependencias de Python en venv dedicado (cacheado por Docker layer)
RUN uv venv /app/.venv && uv pip install --python /app/.venv/bin/python -r pyproject.toml

# Copiar código de la aplicación
COPY --chown=appuser:appuser . .

# Dar permisos de ejecución al entrypoint (como root, antes de cambiar usuario)
RUN chmod +x /app/entrypoint.sh

# Cambiar a usuario no-root para seguridad
USER appuser

# Exponer puerto (Flet usa puerto dinámico, pero podemos configurarlo)
EXPOSE 8550

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8550/ || exit 1

# Entrypoint: migra automáticamente y luego arranca la app
ENTRYPOINT ["/app/entrypoint.sh"]
