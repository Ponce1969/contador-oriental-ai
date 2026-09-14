"""Microservice configuration for voice_api."""

from __future__ import annotations

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    """Voice service configuration settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8553

    # Upload limits (audio files)
    max_upload_size: int = 25 * 1024 * 1024  # 25MB

    # Job Store TTL
    job_ttl_seconds: int = 600  # 10 minutes

    # Faster Whisper settings
    whisper_model: str = "base"
    whisper_compute_type: str = "int8"
    whisper_threads: int = 4  # Optimized for RK3588 Cortex-A76 cores
    whisper_language: str = "es"

    # Ollama Local LLM
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "gemma2:2b"


settings = Settings()
