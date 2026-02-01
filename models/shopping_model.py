from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class ShoppingItem(BaseModel):
    id: int | None = None
    name: str = Field(min_length=1)
    price: float = Field(gt=0)
    category: str
    purchased: bool = False
    purchase_date: date | None = None
