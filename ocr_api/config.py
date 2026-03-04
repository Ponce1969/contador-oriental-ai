"""Configuración del microservicio."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8551

    # Database
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "auditor_familiar"
    postgres_user: str = "auditor_user"
    postgres_password: str

    # Upload
    max_upload_size: int = 10 * 1024 * 1024  # 10MB

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma2:2b"

    @property
    def database_url(self) -> str:
        """URL de conexión."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
