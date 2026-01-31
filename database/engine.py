from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from configs.database_config import DatabaseConfig

# Obtener URL de base de datos según configuración
DATABASE_URL: str = DatabaseConfig.get_database_url()

# Configuración específica según tipo de BD
engine_kwargs = {
    "echo": False,
    "future": True,
}

# Para PostgreSQL, agregar configuración de pool
if DatabaseConfig.is_postgresql():
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,  # Verificar conexiones antes de usar
    })

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)


def get_session() -> Session:
    return SessionLocal()
