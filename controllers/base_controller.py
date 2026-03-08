"""
BaseController: context manager de sesión centralizado.
Todos los controllers de dominio heredan de aquí para evitar
duplicar el patrón _get_session en cada uno.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from core.events import EventSystem
from core.events import event_system as _default_event_system
from core.sqlalchemy_session import get_db_session


class BaseController:
    """
    Base para controllers que necesitan acceso a la base de datos.
    Centraliza el context manager de sesión que antes se duplicaba
    en ExpenseController, IncomeController, FamilyMemberController
    y ShoppingController.
    """

    def __init__(
        self,
        session: Session | None = None,
        familia_id: int | None = None,
        event_system: EventSystem | None = None,
    ) -> None:
        self._session = session
        self._familia_id = familia_id
        self._event_system = (
            event_system if event_system is not None else _default_event_system
        )

    @contextmanager
    def _get_session(self) -> Generator[Session, None, None]:
        """Obtener sesión de base de datos."""
        if self._session:
            yield self._session
        else:
            with get_db_session() as session:
                yield session

    def get_title(self) -> str:
        """Título de la vista asociada. Sobreescribir en subclases."""
        return ""
