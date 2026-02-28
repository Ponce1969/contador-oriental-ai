"""
Configuración de base de datos
Usa PostgreSQL exclusivamente. SQLite deshabilitado.
"""
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

# Cargar variables de entorno desde .env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

DatabaseType = Literal["sqlite", "postgresql"]

class DatabaseConfig:
    """Configuración de base de datos"""
    
    # Tipo de base de datos desde variable de entorno
    DB_TYPE: DatabaseType = os.getenv("DB_TYPE", "postgresql")  # type: ignore

    # SQLite deshabilitado — el proyecto usa PostgreSQL exclusivamente
    # SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "shopping.db")
    
    # Configuración PostgreSQL (producción)
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "auditor_familiar")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
    
    @classmethod
    def get_database_url(cls) -> str:
        """Obtener URL de conexión según el tipo de BD configurado"""
        if cls.DB_TYPE == "sqlite":
            sqlite_path = os.getenv("SQLITE_DB_PATH", "shopping.db")
            return f"sqlite:///{sqlite_path}"
        else:
            return (
                f"postgresql://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}"
                f"@{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"
            )
    
    @classmethod
    def is_postgresql(cls) -> bool:
        """Verificar si se está usando PostgreSQL"""
        return cls.DB_TYPE == "postgresql"
