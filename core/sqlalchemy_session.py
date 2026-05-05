"""
Sesión de SQLAlchemy para fleting.

Delegado a UnitOfWork. Solo para backward compatibility — nuevo código
debería usar UnitOfWork directamente.
"""

from __future__ import annotations

from core.unit_of_work import UnitOfWork, get_db_session, get_db_session_injected


def create_tables() -> None:
    """Crear todas las tablas de la base de datos."""
    from database.base import Base
    from database.engine import engine
    from database.tables import (  # noqa: F401
        ExpenseTable,
        FamilyMemberTable,
        IncomeTable,
    )

    Base.metadata.create_all(bind=engine)
