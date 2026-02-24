from __future__ import annotations

from result import Result

from controllers.base_controller import BaseController
from models.errors import AppError
from models.shopping_model import ShoppingItem
from repositories.shopping_repository import ShoppingRepository
from services.shopping_service import ShoppingService


class ShoppingController(BaseController):
    """
    Controller for shopping page
    """

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
