FROM python:3.12-slim-bookworm

# System dependencies: ffmpeg is required for audio decoding (webm, m4a, wav, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv for fast, reliable package installations
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Install Python dependencies
COPY pyproject.toml .
RUN uv pip install --system --no-cache -r pyproject.toml

# Pre-download Whisper model at build time to prevent runtime downloads on ARM64
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"

# Copy application source code
COPY . /app/voice_api/

# Ensure entrypoint is executable
RUN chmod +x /app/voice_api/entrypoint.sh

EXPOSE 8553

ENTRYPOINT ["/app/voice_api/entrypoint.sh"]
