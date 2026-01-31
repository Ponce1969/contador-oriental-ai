"""
Configuración de base de datos
Soporta SQLite (desarrollo) y PostgreSQL (producción)
"""
import os
from typing import Literal

DatabaseType = Literal["sqlite", "postgresql"]

class DatabaseConfig:
    """Configuración de base de datos"""
    
    # Tipo de base de datos (cambiar a "postgresql" para producción)
    DB_TYPE: DatabaseType = "sqlite"
    
    # Configuración SQLite (desarrollo)
    SQLITE_DB_PATH = "shopping.db"
    
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
            return f"sqlite:///{cls.SQLITE_DB_PATH}"
        else:
            return (
                f"postgresql://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}"
                f"@{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"
            )
    
    @classmethod
    def is_postgresql(cls) -> bool:
        """Verificar si se está usando PostgreSQL"""
        return cls.DB_TYPE == "postgresql"
