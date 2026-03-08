FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

# Dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc libpq-dev curl \
    tesseract-ocr tesseract-ocr-spa \
    libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

# uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Dependencias (como root)
COPY pyproject.toml ./
RUN uv pip install --system -r pyproject.toml

# Usuario
RUN useradd -m -u 1000 ocruser && chown -R ocruser:ocruser /app

# Código - copiar archivos Python al directorio ocr_api
COPY --chown=ocruser:ocruser __init__.py config.py main.py models.py ./ocr_api/

# Entrypoint
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x /app/entrypoint.sh

USER ocruser

EXPOSE 8551

# Espera a Postgres y luego arranca uvicorn
ENTRYPOINT ["/app/entrypoint.sh"]
