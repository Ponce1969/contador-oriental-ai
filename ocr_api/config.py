"""Microservice configuration."""

from __future__ import annotations

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    """OCR service configuration settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8551

    # Upload limits
    max_upload_size: int = 25 * 1024 * 1024  # 25MB (mobile cameras)

    # Job Store TTL
    job_ttl_seconds: int = 600  # 10 minutes

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"

    # Gemini Cloud OCR
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"


settings = Settings()
