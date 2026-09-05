"""Microservice configuration."""

from __future__ import annotations

from pydantic_settings import (  # type: ignore[import-not-found]
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    """OCR service configuration settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8551

    # Upload
    max_upload_size: int = 10 * 1024 * 1024  # 10MB

    # Job Store TTL
    job_ttl_seconds: int = 600  # 10 minutes

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma2:2b"


settings = Settings()
