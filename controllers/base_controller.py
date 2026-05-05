"""
BaseController: inyección de UnitOfWork centralizado.
Todos los controllers de dominio heredan de aquí para evitar
duplicar el patrón de sesión en cada uno.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from core.events import EventSystem
from core.events import event_system as _default_event_system
from core.unit_of_work import UnitOfWork


class BaseController:
    """
    Base para controllers que necesitan acceso a la base de datos.
    Centraliza el UnitOfWork que antes se duplicaba en ExpenseController,
    IncomeController, FamilyMemberController y ShoppingController.

    Uso con inyección (nuevo patrón):
        uow = UnitOfWork(session=injected_session)
        controller = MyController(uow=uow)

    Uso standalone (backward compatible):
        controller = MyController()

    También acepta sesión directa para backward compatibility:
        controller = MyController(session=db_session)
    """

    def __init__(
        self,
        session: Session | None = None,
        familia_id: int | None = None,
        event_system: EventSystem | None = None,
        uow: UnitOfWork | None = None,
    ) -> None:
        self._session = session
        self._familia_id = familia_id
        self._event_system = (
            event_system if event_system is not None else _default_event_system
        )
        self._uow = uow

    @contextmanager
    def _get_session(self) -> Generator[Session, None, None]:
        """
        Obtener sesión de base de datos.

        Prioridad:
        1. Si hay _uow inyectado, lo usa
        2. Si hay _session directo (backward compat), lo yield
        3. Caso contrario, crea UnitOfWork internamente
        """
        if self._uow is not None:
            with self._uow as uow:
                yield uow.session
        elif self._session is not None:
            yield self._session
        else:
            with UnitOfWork() as uow:
                yield uow.session

    def get_title(self) -> str:
        """Título de la vista asociada. Sobreescribir en subclases."""
        return ""
