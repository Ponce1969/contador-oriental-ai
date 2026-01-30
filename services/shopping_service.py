from __future__ import annotations

from result import Err, Result

from models.errors import DatabaseError, ValidationError
from models.shopping_model import ShoppingItem
from repositories.shopping_repository import ShoppingRepository


class ShoppingService:
    def __init__(self, repo: ShoppingRepository) -> None:
        self._repo = repo

    def create_item(
        self, item: ShoppingItem
    ) -> Result[ShoppingItem, ValidationError | DatabaseError]:
        if item.price <= 0:
            return Err(ValidationError("El precio debe ser mayor a 0"))

        return self._repo.add(item)

    def list_items(self):
        return self._repo.list_all()
