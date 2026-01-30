from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from result import Result
from sqlalchemy.orm import Session

from core.sqlalchemy_session import get_db_session
from models.errors import AppError
from models.shopping_model import ShoppingItem
from repositories.shopping_repository import ShoppingRepository
from services.shopping_service import ShoppingService


class ShoppingController:
    """
    Controller for shopping page
    """

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    @contextmanager
    def _get_session(self) -> Generator[Session, None, None]:
        """Obtener sesión de base de datos."""
        if self._session:
            yield self._session
        else:
            with get_db_session() as session:
                yield session

    def get_title(self) -> str:
        return "Shopping"

    def add_item(self, item: ShoppingItem) -> Result[ShoppingItem, AppError]:
        with self._get_session() as session:
            repo = ShoppingRepository(session)
            service = ShoppingService(repo)
            return service.create_item(item)

    def list_items(self) -> list[ShoppingItem]:
        with self._get_session() as session:
            repo = ShoppingRepository(session)
            service = ShoppingService(repo)
            return service.list_items()
