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
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root para seguridad
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# Establecer directorio de trabajo
WORKDIR /app

# Instalar uv (gestor de paquetes rápido)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Copiar archivos de dependencias
COPY --chown=appuser:appuser pyproject.toml ./

# Instalar dependencias de Python
RUN uv pip install --system -r pyproject.toml

# Copiar código de la aplicación
COPY --chown=appuser:appuser . .

# Cambiar a usuario no-root
USER appuser

# Exponer puerto (Flet usa puerto dinámico, pero podemos configurarlo)
EXPOSE 8550

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8550/ || exit 1

# Comando por defecto
CMD ["python", "main.py"]
