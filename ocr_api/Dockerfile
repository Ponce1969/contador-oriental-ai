FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

# System dependencies (ARM optimized: no build-essential/gcc/libpq-dev needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tesseract-ocr \
    tesseract-ocr-spa \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Dependencies installation
COPY pyproject.toml ./
RUN uv pip install --system -r pyproject.toml

# Non-root user
RUN useradd -m -u 1000 ocruser && chown -R ocruser:ocruser /app

# Source code
COPY --chown=ocruser:ocruser __init__.py config.py main.py models.py ./ocr_api/

# Entrypoint
COPY --chown=ocruser:ocruser entrypoint.sh ./entrypoint.sh
RUN chmod +x /app/entrypoint.sh

USER ocruser

EXPOSE 8551

ENTRYPOINT ["/app/entrypoint.sh"]
