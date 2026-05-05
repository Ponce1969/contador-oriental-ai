"""
Unit of Work — El árbitro central de transacciones.

Centraliza el manejo de sesiones de base de datos para garantizar:
- atomicidad: todo o nada
- una sola fuente de verdad: una sesión por request
- commit/rollback automático según el resultado

Patrón extraído de Fowler "Patterns of Enterprise Application Architecture"
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from typing import Self


class UnitOfWork:
    """
    Context manager que centraliza el manejo de transacciones.

    Uso:
        # Inyección (FastAPI Depends)
        uow = UnitOfWork(session=injected_session)

        # Creación standalone (backwards compatibility)
        with UnitOfWork() as uow:
            repo = MyRepository(uow.session)
            repo.add(entity)
        # Commit automático al salir, o rollback si hay excepción
    """

    def __init__(
        self,
        session: Session | None = None,
    ) -> None:
        self._injected_session = session
        self._session: Session | None = None

    @property
    def session(self) -> Session:
        """Acceso a la sesión activa. Debe usarse dentro del context manager."""
        if self._session is None:
            raise RuntimeError(
                "UnitOfWork.session accessed outside of context. "
                "Use 'with UnitOfWork() as uow:' pattern."
            )
        return self._session

    def __enter__(self) -> Self:
        if self._injected_session is not None:
            self._session = self._injected_session
        else:
            from database.engine import SessionLocal

            self._session = SessionLocal()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if self._session is None:
            return False

        if exc_type is not None:
            self._session.rollback()
            return False

        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        finally:
            if self._injected_session is None:
                self._session.close()

        return True

    def rollback(self) -> None:
        """Permite rollback manual si el caller necesita cancelar."""
        if self._session is not None:
            self._session.rollback()

    def flush(self) -> None:
        """Flush forzado de cambios (para validaciones previas al commit)."""
        if self._session is not None:
            self._session.flush()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager legacy para backward compatibility.

    NUEVO CÓDIGO DEBERÍA usar UnitOfWork() directamente.
    Este existe solo para no romper código existente.
    """
    with UnitOfWork() as uow:
        yield uow.session


def get_db_session_injected(session: Session) -> Generator[Session, None, None]:
    """
    Para uso con FastAPI Depends — pasa la sesión injectada.
    El commit/rollback lo maneja el UnitOfWork del caller.
    """
    yield session