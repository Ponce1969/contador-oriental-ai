from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class Household(BaseModel, frozen=True):
    id: int | None = None
    nombre: str = Field(min_length=1, max_length=100)
    status: str = "active"
    created_at: datetime | None = None


class HouseholdMember(BaseModel, frozen=True):
    id: int | None = None
    household_id: int
    familia_id: int
    role: str  # "admin" | "member"
    joined_at: datetime | None = None


class HouseholdInvitation(BaseModel, frozen=True):
    id: int | None = None
    household_id: int
    token: str
    status: str = "pending"  # "pending" | "accepted" | "revoked" | "expired"
    expires_at: datetime
    created_at: datetime | None = None


class HouseholdJoinResult(BaseModel, frozen=True):
    household_id: int
    nombre: str
    active_member_count: int


class SharedExpenseLink(BaseModel, frozen=True):
    id: int | None = None
    household_id: int
    gasto_id: int
    familia_id: int
    linked_at: datetime | None = None


class SharedExpenseFeedItem(BaseModel, frozen=True):
    gasto_id: int
    household_id: int
    familia_id: int
    familia_nombre: str
    monto: Decimal
    currency: str
    fecha: date
    descripcion: str
    categoria: str


class MemberBalance(BaseModel, frozen=True):
    familia_id: int
    familia_nombre: str
    total_contributed: Decimal
    equal_share: Decimal
    net_balance: Decimal  # positive = owed money; negative = owes money


class HouseholdSettlement(BaseModel, frozen=True):
    id: int | None = None
    household_id: int
    payer_familia_id: int
    recipient_familia_id: int
    monto: Decimal = Field(gt=Decimal("0"))
    fecha: date
    created_at: datetime | None = None


class ExpenseFeedPage(BaseModel, frozen=True):
    items: list[SharedExpenseFeedItem]
    total_count: int
    page: int
    page_size: int
