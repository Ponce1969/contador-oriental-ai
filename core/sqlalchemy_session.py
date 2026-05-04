"""
Sesión de SQLAlchemy para fleting

 reutiliza el SessionLocal de database.engine para evitar
crear múltiples sessionmakers que causarían inconsistencias.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from database.engine import SessionLocal, engine


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager para sesión de base de datos.

    Reutiliza SessionLocal de database/engine.py (singleton real).
    Cada llamada crea una nueva sesión del pool, asegurandoIsolation.
    Commit al salir, rollback en excepción.
    """
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
    from database.tables import (  # noqa: F401
        ExpenseTable,
        FamilyMemberTable,
        IncomeTable,
    )

    Base.metadata.create_all(bind=engine)
