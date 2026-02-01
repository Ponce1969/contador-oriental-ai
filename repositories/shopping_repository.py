from __future__ import annotations

from collections.abc import Sequence

from result import Err, Ok, Result
from sqlalchemy.orm import Session

from database.tables import ShoppingItemTable
from models.errors import DatabaseError
from models.shopping_model import ShoppingItem
from repositories.mappers import shopping_to_domain, shopping_to_table


class ShoppingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, item: ShoppingItem) -> Result[ShoppingItem, DatabaseError]:
        try:
            row = shopping_to_table(item)
            self._session.add(row)
            self._session.commit()
            self._session.refresh(row)
            return Ok(shopping_to_domain(row))
        except Exception as exc:  # encapsulado
            return Err(DatabaseError(str(exc)))

    def list_all(self) -> Result[Sequence[ShoppingItem], DatabaseError]:
        try:
            rows = self._session.query(ShoppingItemTable).all()
            return Ok([shopping_to_domain(row) for row in rows])
        except Exception as exc:
            return Err(DatabaseError(str(exc)))
