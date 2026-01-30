"""
Sesión de SQLAlchemy para fleting
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy.orm import Session, sessionmaker

from database.engine import engine


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager para sesión de base de datos.
    
    Usage:
        with get_db_session() as session:
            # usar session aquí
            # commit automático, rollback automático en error
    """
    SessionLocal = sessionmaker(bind=engine)
    
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_tables() -> None:
    """Crear todas las tablas de la base de datos."""
    from database.base import Base
    from database.tables import ExpenseTable  # noqa: F401
    
    Base.metadata.create_all(bind=engine)
