# Design Document — Shared Household Expenses

## Overview

The Shared Household Expenses feature introduces a new cross-family entity — a **Household** (`hogar`) — that lets two or more existing family accounts collaboratively track a subset of their expenses without breaking the existing multi-tenant isolation model.

The design follows the established MVC + Services + Repositories layering already present in the codebase. Nothing in the existing `expenses`, `familias`, or `usuarios` tables changes shape; the feature is additive. Shared expenses are not duplicated — a `shared_expense_links` join table is the single bridge between an existing `expenses` row and a `household`.

Key design decisions:
- **No new user concept**: a Household is a relationship between existing `familias` records, not between individual `usuarios`.
- **Equal-split balance**: computed purely in Python with `Decimal` arithmetic on every request; never cached.
- **Token-based invitations**: 48-hour, single-use, revocable — no email integration required.
- **Audit trail**: every link creation/deletion appended to `household_audit_log` at the repository layer, not the service layer.
- **AI scoping**: household context is additive to the existing `ai_vector_memory` table via a nullable `household_id` column; personal scoping is unchanged.

---

## Architecture

The new modules slot into the existing layers without modifying them:

```
┌────────────────────────────────────────────────────────────────────┐
│  Flet UI  (views/pages/household_view.py)                          │
│  Three-tab layout: Gastos | Balance | Miembros                     │
└────────────────────────┬───────────────────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────────────────┐
│  HouseholdController   (controllers/household_controller.py)       │
│  Inherits BaseController — uses _get_session() context manager     │
└──┬──────────┬──────────┬──────────┬──────────┬─────────────────────┘
   │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼
HouseholdSvc  InvitSvc  SharingSvc  BalanceSvc  SettlementSvc
(services/domain/household/)
   │          │          │          │          │
   └──────────┴──────────┴──────────┴──────────┘
                         │
              Repositories (repositories/household/)
              HouseholdRepo | InvitationRepo | SharedExpenseLinkRepo
              BalanceRepo   | SettlementRepo | AuditLogRepo
                         │
              PostgreSQL tables (household group)
              hogares | household_members | household_invitations
              shared_expense_links | household_settlements
              household_audit_log | ai_vector_memory (+household_id)
```

**Event flow for AI vectorization:**

```
HouseholdController.share_expense()
  → ExpenseSharingService.create_link()
    → SharedExpenseLinkRepository.add()
    → event_system.fire_and_forget(Event(SHARED_EXPENSE_LINK_CREADO))
      → HouseholdMemoryHandler.handle()  (async, background)
        → EmbeddingService.generar_embedding()
        → MemoriaRepository.guardar() with household_id tag
```

---

## Components and Interfaces

### Service Layer — `services/domain/household/`

#### `HouseholdService`

```python
class HouseholdService:
    def __init__(
        self,
        household_repo: HouseholdRepository,
        member_repo: HouseholdMemberRepository,
        link_repo: SharedExpenseLinkRepository,
        settlement_repo: HouseholdSettlementRepository,
    ) -> None: ...

    def create_household(
        self, familia_id: int, nombre: str
    ) -> Result[Household, HouseholdConflictError | ValidationError | DatabaseError]:
        # 1. Check membership conflict FIRST (before name validation)
        # 2. Validate and trim name (1-100 chars)
        # 3. Create hogares row + household_members row (admin role) atomically

    def leave_household(
        self, familia_id: int, household_id: int
    ) -> Result[None, AdminMustTransferError | NotAMemberError | BalanceNotZeroError | DatabaseError]:
        # Block if net_balance != 0 (BalanceNotZeroError)
        # Non-admin: atomically delete member + their shared_expense_links
        # Admin-only: atomically disband (set status=disbanded, delete all members + links)
        # Admin with others: return AdminMustTransferError

    def transfer_admin(
        self, admin_familia_id: int, target_familia_id: int, household_id: int
    ) -> Result[None, UnauthorizedError | NotAMemberError | DatabaseError]:
        # Verify admin_familia_id is active admin
        # Verify target_familia_id is active member
        # Atomically swap roles (admin -> member, member -> admin)

    def get_household_for_familia(
        self, familia_id: int
    ) -> Result[Household | None, DatabaseError]:
        # Returns the active household for a familia_id, or None
```

#### `InvitationService`

```python
class InvitationService:
    def __init__(
        self,
        invitation_repo: HouseholdInvitationRepository,
        member_repo: HouseholdMemberRepository,
    ) -> None: ...

    def create_invitation(
        self, household_id: int, admin_familia_id: int
    ) -> Result[HouseholdInvitation, InvitationLimitError | NotAMemberError | DatabaseError]:
        # Check admin is member with admin role
        # Check active invitation count < 10
        # Generate secure token (secrets.token_urlsafe(32))
        # Set expires_at = now + 48h

    def accept_invitation(
        self, token: str, familia_id: int
    ) -> Result[HouseholdJoinResult, InvalidInvitationError | HouseholdConflictError | DatabaseError]:
        # Check token valid (not expired/accepted/revoked) — BEFORE conflict check? No:
        # Req 2.5: membership conflict check on accept → InvalidInvitationError if token bad, HouseholdConflictError if member conflict
        # Atomically: mark invitation accepted + create household_members row

    def revoke_invitation(
        self, token: str, admin_familia_id: int, household_id: int
    ) -> Result[None, InvalidInvitationError | NotAMemberError | DatabaseError]:
        # Verify admin role
        # Verify invitation is pending (status == pending)
        # Mark as revoked
```

#### `ExpenseSharingService`

```python
class ExpenseSharingService:
    def __init__(
        self,
        link_repo: SharedExpenseLinkRepository,
        expense_repo: ExpenseRepository,
        member_repo: HouseholdMemberRepository,
        audit_repo: HouseholdAuditLogRepository,
    ) -> None: ...

    def create_link(
        self, gasto_id: int, household_id: int, familia_id: int
    ) -> Result[SharedExpenseLink, NotFoundError | UnauthorizedError | NotAMemberError | DuplicateLinkError | DatabaseError]:
        # 1. Verify familia_id is active member of household_id
        # 2. Load gasto — NotFoundError if missing
        # 3. Check gasto.familia_id == familia_id — UnauthorizedError BEFORE duplicate check
        # 4. Check no existing active link for (gasto_id, household_id) — DuplicateLinkError
        # 5. Insert shared_expense_links row
        # 6. Append audit log (created)

    def delete_link(
        self, gasto_id: int, household_id: int, familia_id: int
    ) -> Result[None, NotFoundError | NotAMemberError | DatabaseError]:
        # 1. Verify familia_id is active member
        # 2. Find link — NotFoundError if missing
        # 3. Delete link row
        # 4. Append audit log (deleted)

    def create_expense_and_link(
        self, expense: Expense, household_id: int, familia_id: int
    ) -> Result[tuple[Expense, SharedExpenseLink], ...]:
        # Atomic: create expense row + link row; rollback both on any failure
```


#### `HouseholdBalanceService`

```python
class HouseholdBalanceService:
    def __init__(
        self,
        link_repo: SharedExpenseLinkRepository,
        settlement_repo: HouseholdSettlementRepository,
        member_repo: HouseholdMemberRepository,
    ) -> None: ...

    def compute_balance(
        self,
        household_id: int,
        familia_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Result[list[MemberBalance], ValidationError | UnauthorizedError | DatabaseError]:
        # 1. If period supplied, validate start_date <= end_date (ValidationError if not)
        # 2. Verify familia_id is active member (UnauthorizedError if not)
        # 3. Fetch active members list
        # 4. Sum monto of shared_expense_links per member (filtered by period)
        # 5. Sum household_settlements per member (as payer/recipient, filtered by period)
        # 6. Compute total = sum of all contributions
        # 7. equal_share = total / len(active_members) — Decimal division
        # 8. net_balance = contributions[m] + settlements_paid[m] - settlements_received[m] - equal_share
        # Never uses float; uses Decimal("0") as accumulator start
```

#### `SettlementService`

```python
class SettlementService:
    def __init__(
        self,
        settlement_repo: HouseholdSettlementRepository,
        member_repo: HouseholdMemberRepository,
        event_system: EventSystem,
    ) -> None: ...

    def record_settlement(
        self,
        household_id: int,
        payer_familia_id: int,
        recipient_familia_id: int,
        monto: Decimal,
        fecha: date,
        authenticated_familia_id: int,
    ) -> Result[HouseholdSettlement, UnauthorizedError | NotAMemberError | ValidationError | DatabaseError]:
        # 1. authenticated_familia_id must equal payer_familia_id (UnauthorizedError)
        # 2. payer != recipient (ValidationError)
        # 3. monto > Decimal("0") (ValidationError)
        # 4. Both payer and recipient must be active members (NotAMemberError)
        # 5. Create settlement record
        # 6. fire_and_forget(Event(SETTLEMENT_CREADO, ...))
```

### Repository Layer — `repositories/household/`

```python
class HouseholdRepository:
    def create(self, nombre: str, familia_id: int) -> HouseholdTable
    def get_by_id(self, household_id: int) -> HouseholdTable | None
    def set_disbanded(self, household_id: int) -> None

class HouseholdMemberRepository:
    def get_active_membership(self, familia_id: int) -> HouseholdMemberTable | None
    def get_members(self, household_id: int) -> list[HouseholdMemberTable]
    def add_member(self, household_id: int, familia_id: int, role: str) -> HouseholdMemberTable
    def remove_member(self, household_id: int, familia_id: int) -> None
    def is_active_member(self, household_id: int, familia_id: int) -> bool
    def get_member_role(self, household_id: int, familia_id: int) -> str | None

class HouseholdInvitationRepository:
    def create(self, household_id: int, token: str, expires_at: datetime) -> HouseholdInvitationTable
    def get_by_token(self, token: str) -> HouseholdInvitationTable | None
    def count_active(self, household_id: int) -> int
    def mark_accepted(self, invitation_id: int) -> None
    def mark_revoked(self, invitation_id: int) -> None

class SharedExpenseLinkRepository:
    def create(self, gasto_id: int, household_id: int, familia_id: int) -> SharedExpenseLinkTable
    def get_by_gasto_and_household(self, gasto_id: int, household_id: int) -> SharedExpenseLinkTable | None
    def delete_by_gasto_and_household(self, gasto_id: int, household_id: int) -> None
    def delete_all_for_member(self, household_id: int, familia_id: int) -> int  # returns count deleted
    def delete_all_for_household(self, household_id: int) -> int
    def get_feed(
        self, household_id: int,
        start_date: date | None, end_date: date | None,
        filter_familia_id: int | None,
        page: int, page_size: int,
    ) -> tuple[list[SharedExpenseFeedItem], int]  # (items, total_count)
    def sum_contributions_per_member(
        self, household_id: int,
        start_date: date | None, end_date: date | None,
    ) -> dict[int, Decimal]  # familia_id → total

class HouseholdSettlementRepository:
    def create(self, household_id: int, payer: int, recipient: int, monto: Decimal, fecha: date) -> HouseholdSettlementTable
    def sum_per_member(
        self, household_id: int,
        start_date: date | None, end_date: date | None,
    ) -> dict[int, dict[str, Decimal]]  # {familia_id: {paid: Decimal, received: Decimal}}

class HouseholdAuditLogRepository:
    def append(self, familia_id: int, gasto_id: int, household_id: int, action: str) -> None
```

### Controller Layer — `controllers/household_controller.py`

```python
class HouseholdController(BaseController):
    def __init__(self, session=None, familia_id=None, uow=None) -> None: ...

    # Household lifecycle
    def create_household(self, nombre: str) -> Result[Household, AppError]
    def leave_household(self, household_id: int) -> Result[None, AppError]
    def transfer_admin(self, target_familia_id: int, household_id: int) -> Result[None, AppError]
    def get_current_household(self) -> Result[Household | None, AppError]

    # Invitations
    def invite_family(self, household_id: int) -> Result[HouseholdInvitation, AppError]
    def accept_invitation(self, token: str) -> Result[HouseholdJoinResult, AppError]
    def revoke_invitation(self, token: str, household_id: int) -> Result[None, AppError]

    # Expense sharing
    def share_expense(self, gasto_id: int, household_id: int) -> Result[SharedExpenseLink, AppError]
    def unshare_expense(self, gasto_id: int, household_id: int) -> Result[None, AppError]
    def create_and_share_expense(self, expense: Expense, household_id: int) -> Result[tuple[Expense, SharedExpenseLink], AppError]

    # Feed & balance
    def get_expense_feed(
        self, household_id: int,
        start_date: date | None = None, end_date: date | None = None,
        filter_familia_id: int | None = None,
        page: int = 1, page_size: int = 20,
    ) -> Result[tuple[list[SharedExpenseFeedItem], int], AppError]

    def get_balance(
        self, household_id: int,
        start_date: date | None = None, end_date: date | None = None,
    ) -> Result[list[MemberBalance], AppError]

    # Settlements
    def record_settlement(
        self, household_id: int,
        recipient_familia_id: int, monto: Decimal, fecha: date,
    ) -> Result[HouseholdSettlement, AppError]
```

---

## Data Models

### New SQLAlchemy Tables (`database/tables.py` additions)

```python
class HogarTable(Base):
    __tablename__ = "hogares"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    # status: "active" | "disbanded"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (
        Index("idx_hogares_status", "status"),
    )


class HouseholdMemberTable(Base):
    __tablename__ = "household_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("hogares.id", ondelete="CASCADE"), nullable=False
    )
    familia_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("familias.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    # role: "admin" | "member"
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("household_id", "familia_id", name="uq_household_member"),
        Index("idx_household_members_familia", "familia_id"),
        Index("idx_household_members_household", "household_id"),
    )


class HouseholdInvitationTable(Base):
    __tablename__ = "household_invitations"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("hogares.id", ondelete="CASCADE"), nullable=False
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # status: "pending" | "accepted" | "revoked" | "expired"
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    accepted_by_familia_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("familias.id", ondelete="SET NULL"), nullable=True
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_invitations_token", "token"),
        Index("idx_invitations_household_status", "household_id", "status"),
    )


class SharedExpenseLinkTable(Base):
    __tablename__ = "shared_expense_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("hogares.id", ondelete="CASCADE"), nullable=False
    )
    gasto_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False
    )
    familia_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("familias.id", ondelete="CASCADE"), nullable=False
    )
    linked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("household_id", "gasto_id", name="uq_household_gasto_link"),
        Index("idx_shared_links_household", "household_id"),
        Index("idx_shared_links_familia", "familia_id"),
        Index("idx_shared_links_gasto", "gasto_id"),
    )


class HouseholdSettlementTable(Base):
    __tablename__ = "household_settlements"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("hogares.id", ondelete="RESTRICT"), nullable=False
    )
    payer_familia_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("familias.id", ondelete="RESTRICT"), nullable=False
    )
    recipient_familia_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("familias.id", ondelete="RESTRICT"), nullable=False
    )
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_settlements_household", "household_id"),
        Index("idx_settlements_payer", "payer_familia_id"),
        Index("idx_settlements_recipient", "recipient_familia_id"),
        Index("idx_settlements_fecha", "household_id", "fecha"),
    )


class HouseholdAuditLogTable(Base):
    __tablename__ = "household_audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("hogares.id", ondelete="CASCADE"), nullable=False
    )
    familia_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("familias.id", ondelete="CASCADE"), nullable=False
    )
    gasto_id: Mapped[int] = mapped_column(Integer, nullable=False)
    # gasto_id is stored as plain int — if the expense is deleted, the audit record remains
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    # action: "created" | "deleted"
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_audit_log_household", "household_id"),
        Index("idx_audit_log_familia", "familia_id"),
    )
```

**Migration for `ai_vector_memory` — add `household_id` column:**

```sql
ALTER TABLE ai_vector_memory
    ADD COLUMN IF NOT EXISTS household_id INTEGER REFERENCES hogares(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_ai_vector_memory_household
    ON ai_vector_memory (household_id)
    WHERE household_id IS NOT NULL;
```

The column is `nullable` — existing personal vectors are unaffected. Household-scoped vectors have a non-null `household_id`.

---

### New Pydantic Domain Models (`models/household_model.py`)

```python
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
```

---

### New Custom Errors (`models/errors.py` additions)

```python
@dataclass(frozen=True)
class NotFoundError(AppError):
    pass


@dataclass(frozen=True)
class UnauthorizedError(AppError):
    pass


@dataclass(frozen=True)
class HouseholdConflictError(AppError):
    """Raised when a familia is already an active member of a Household."""
    pass


@dataclass(frozen=True)
class AdminMustTransferError(AppError):
    """Raised when an admin tries to leave a Household with other active members."""
    pass


@dataclass(frozen=True)
class BalanceNotZeroError(AppError):
    """Raised when a member tries to leave a Household but their net balance is not zero."""
    pass


@dataclass(frozen=True)
class NotAMemberError(AppError):
    """Raised when the familia is not an active member of the target Household."""
    pass


@dataclass(frozen=True)
class InvalidInvitationError(AppError):
    """Raised when a token is expired, already accepted, or revoked."""
    pass


@dataclass(frozen=True)
class InvitationLimitError(AppError):
    """Raised when the Household already has 10 active pending invitations."""
    pass


@dataclass(frozen=True)
class DuplicateLinkError(AppError):
    """Raised when the (gasto_id, household_id) pair already has an active link."""
    pass
```

---

## Event System

### New `EventType` values (`core/events.py`)

```python
class EventType(Enum):
    # ... existing values ...
    SHARED_EXPENSE_LINK_CREADO = "shared_expense_link_creado"
    SHARED_EXPENSE_LINK_ELIMINADO = "shared_expense_link_eliminado"
    SETTLEMENT_CREADO = "settlement_creado"
```

### New Event `data` payloads

**`SHARED_EXPENSE_LINK_CREADO`**:
```python
{
    "gasto_id": int,
    "household_id": int,
    "familia_id": int,
    "familia_nombre": str,
    "descripcion": str,
    "monto": str,          # str(Decimal) to avoid float contamination
    "categoria": str,
    "fecha": str,          # ISO date string
}
```

**`SHARED_EXPENSE_LINK_ELIMINADO`**:
```python
{
    "gasto_id": int,
    "household_id": int,
    "familia_id": int,
}
```

**`SETTLEMENT_CREADO`**:
```python
{
    "household_id": int,
    "payer_familia_id": int,
    "recipient_familia_id": int,
    "monto": str,          # str(Decimal)
    "fecha": str,
}
```

### New Event Handler — `services/ai/household_memory_handler.py`

```python
async def handle_shared_expense_link_creado(event: Event) -> None:
    """
    Vectorize a newly shared expense into ai_vector_memory tagged with
    both familia_id and household_id.
    """
    data = event.data
    texto = (
        f"Gasto compartido en hogar: {data['descripcion']} "
        f"- ${data['monto']} {data['categoria']} "
        f"por {data['familia_nombre']} el {data['fecha']}"
    )
    # Store with household_id tag so household AI context queries can find it
    with UnitOfWork() as uow:
        repo = MemoriaRepository(uow.session, familia_id=event.familia_id)
        embedding_svc = EmbeddingService()
        memory_svc = IAMemoryService(repo, embedding_svc)
        await memory_svc.registrar_evento_contable(
            texto_plano=texto,
            source_type="shared_expense",
            source_id=data["gasto_id"],
            household_id=data["household_id"],   # new kwarg passed to repo
        )


async def handle_shared_expense_link_eliminado(event: Event) -> None:
    """
    Delete the household-scoped ai_vector_memory record for this expense.
    The family-scoped record (source_type="expense") is untouched.
    """
    data = event.data
    with UnitOfWork() as uow:
        repo = MemoriaRepository(uow.session, familia_id=event.familia_id)
        repo.eliminar_household_vector(
            source_id=data["gasto_id"],
            household_id=data["household_id"],
        )
```

Handler registration occurs in `core/app.py` during startup:

```python
event_system.subscribe(EventType.SHARED_EXPENSE_LINK_CREADO, handle_shared_expense_link_creado)
event_system.subscribe(EventType.SHARED_EXPENSE_LINK_ELIMINADO, handle_shared_expense_link_eliminado)
```

### `MemoriaRepository` changes

Two new methods to support household context:

```python
def guardar_con_household(
    self,
    content: str,
    embedding: list[float],
    source_type: str,
    source_id: int,
    household_id: int,
) -> int | None:
    """
    Insert into ai_vector_memory with household_id set.
    Used for shared-expense vectors.
    """

def eliminar_household_vector(self, source_id: int, household_id: int) -> None:
    """
    Delete the household-scoped vector for a specific expense.
    Matches on source_type='shared_expense', source_id, and household_id.
    """

def buscar_similares_por_household(
    self,
    embedding: list[float],
    household_id: int,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Semantic search scoped exclusively to household_id.
    Used when user queries from the Hogar section.
    """
```

---

## UI Design

### Navigation Changes (`views/layouts/main_layout.py`)

The top navigation bar gains a conditional entry. At layout construction time, `HouseholdController.get_current_household()` is called to determine membership:

```
┌──────────────────────────────────────────────────────────────┐
│  [📊 Dashboard] [💰 Ingresos] [💸 Gastos] ...               │
│  [🏠 Hogar]          ← if active household member            │
│  [🏠 Crear hogar compartido]  ← if NOT a member              │
└──────────────────────────────────────────────────────────────┘
```

Route additions to `configs/routes.py`:

```python
{
    "path": "/hogar",
    "view": "views.pages.household_view.HouseholdView",
    "label": "🏠 Hogar",
    "icon": ft.Icons.HOME_WORK,
    "show_in_top": False,  # shown conditionally in layout, not in static nav list
    "show_in_bottom": False,
},
{
    "path": "/hogar/crear",
    "view": "views.pages.household_create_view.HouseholdCreateView",
    "label": "🏠 Crear hogar",
    "icon": ft.Icons.ADD_HOME,
    "show_in_top": False,
    "show_in_bottom": False,
},
{
    "path": "/hogar/unirse",
    "view": "views.pages.household_join_view.HouseholdJoinView",
    "label": "Unirse a hogar",
    "icon": ft.Icons.HOME_WORK,
    "show_in_top": False,
    "show_in_bottom": False,
},
```

### `HouseholdView` — Three-Tab Layout (`views/pages/household_view.py`)

```
┌─────────────────────────────────────────────────────┐
│  🏠  Mi Hogar Compartido — "Nombre del Hogar"        │
│  ┌──────────┬───────────┬────────────┐              │
│  │  Gastos  │  Balance  │  Miembros  │              │
│  └──────────┴───────────┴────────────┘              │
│                                                     │
│  [Tab content area]                                 │
└─────────────────────────────────────────────────────┘
```

#### Gastos Tab

- On load: populate from local cached list immediately (empty-state message if cache is empty), then refresh from `get_expense_feed()`.
- Each item shows: family display name chip, description, amount (colored by currency), category, date.
- Date range filter row + optional "Filtrar por miembro" dropdown.
- Pagination controls (← page / page → ).
- Optimistic update: when user marks an expense as shared from `ExpensesView`, the new item is prepended to this list immediately via a callback, before the network response.

#### Balance Tab

- On load: call `get_balance()` (always fresh, never cached).
- Each member shown in a card:
  ```
  ┌────────────────────────────────────────┐
  │  👨‍👩‍👧 Familia García                       │
  │  Aportó: $12,500    Cuota justa: $10,000 │
  │  Balance neto: +$2,500 ✅ le deben      │
  └────────────────────────────────────────┘
  ```
- Net balance formatted as signed currency (`+$2,500` / `-$1,200`).
- Period selector (date range picker) to filter by date range.

#### Miembros Tab

- Lists all active members with role badges.
- Admin: invite button (shows invitation token/QR, same pattern as OCR sessions).
- Per-member row: if that member has a non-zero net balance against the authenticated family, a "💸 Registrar pago" button pre-fills the settlement form.
- Settlement form dialog: amount field (Decimal), date picker, confirmation.
- "Abandonar hogar" button at the bottom (red, requires confirmation dialog).

### `HouseholdCreateView` (`views/pages/household_create_view.py`)

Simple form with household name input + confirm button. On success, redirect to `/hogar`.

### `HouseholdJoinView` (`views/pages/household_join_view.py`)

Token input field. On accept, redirect to `/hogar`. Error messages shown inline.

### Flet Guidelines Applied

- `ft.Tabs` with `tab_alignment=ft.TabAlignment.FILL` for the three-tab layout.
- `ft.Button` (not deprecated `ft.ElevatedButton`) for all action buttons.
- No `page.launch_url()` — invitation tokens are shown as copyable text with a `ft.IconButton` copy-to-clipboard action.
- Optimistic updates: mutate the in-memory list and call `page.update()` before awaiting server confirmation.
- Empty-state rendered from a local `_cached_feed: list[SharedExpenseFeedItem]` attribute initialized to `[]` at view construction time.

---

## Migration Strategy

Migrations are created and run via `uv run fleting db make <name>` + `uv run fleting db migrate`. The household migrations must run in this order because of foreign key dependencies:

| Migration file | Description |
|---|---|
| `017_add_household_tables.py` | Creates `hogares`, `household_members`, `household_invitations`, `shared_expense_links`, `household_settlements`, `household_audit_log` |
| `018_add_household_id_to_ai_vector_memory.py` | Adds nullable `household_id` column + index to `ai_vector_memory` |

**Migration 017 up/down sketch:**

```python
def up(db):
    db.execute("""
        CREATE TABLE hogares (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'active',
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    db.execute("""
        CREATE TABLE household_members (
            id SERIAL PRIMARY KEY,
            household_id INTEGER NOT NULL REFERENCES hogares(id) ON DELETE CASCADE,
            familia_id INTEGER NOT NULL REFERENCES familias(id) ON DELETE CASCADE,
            role VARCHAR(20) NOT NULL,
            joined_at TIMESTAMP NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_household_member UNIQUE (household_id, familia_id)
        )
    """)
    db.execute("""
        CREATE TABLE household_invitations (
            id SERIAL PRIMARY KEY,
            household_id INTEGER NOT NULL REFERENCES hogares(id) ON DELETE CASCADE,
            token VARCHAR(64) UNIQUE NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            expires_at TIMESTAMP NOT NULL,
            accepted_by_familia_id INTEGER REFERENCES familias(id) ON DELETE SET NULL,
            accepted_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    db.execute("""
        CREATE TABLE shared_expense_links (
            id SERIAL PRIMARY KEY,
            household_id INTEGER NOT NULL REFERENCES hogares(id) ON DELETE CASCADE,
            gasto_id INTEGER NOT NULL REFERENCES expenses(id) ON DELETE CASCADE,
            familia_id INTEGER NOT NULL REFERENCES familias(id) ON DELETE CASCADE,
            linked_at TIMESTAMP NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_household_gasto_link UNIQUE (household_id, gasto_id)
        )
    """)
    db.execute("""
        CREATE TABLE household_settlements (
            id SERIAL PRIMARY KEY,
            household_id INTEGER NOT NULL REFERENCES hogares(id) ON DELETE RESTRICT,
            payer_familia_id INTEGER NOT NULL REFERENCES familias(id) ON DELETE RESTRICT,
            recipient_familia_id INTEGER NOT NULL REFERENCES familias(id) ON DELETE RESTRICT,
            monto DECIMAL(12,2) NOT NULL,
            fecha DATE NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    db.execute("""
        CREATE TABLE household_audit_log (
            id SERIAL PRIMARY KEY,
            household_id INTEGER NOT NULL REFERENCES hogares(id) ON DELETE CASCADE,
            familia_id INTEGER NOT NULL REFERENCES familias(id) ON DELETE CASCADE,
            gasto_id INTEGER NOT NULL,
            action VARCHAR(20) NOT NULL,
            timestamp TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    # Indexes
    for stmt in [
        "CREATE INDEX idx_hogares_status ON hogares(status)",
        "CREATE INDEX idx_household_members_familia ON household_members(familia_id)",
        "CREATE INDEX idx_household_members_household ON household_members(household_id)",
        "CREATE INDEX idx_invitations_token ON household_invitations(token)",
        "CREATE INDEX idx_invitations_household_status ON household_invitations(household_id, status)",
        "CREATE INDEX idx_shared_links_household ON shared_expense_links(household_id)",
        "CREATE INDEX idx_shared_links_familia ON shared_expense_links(familia_id)",
        "CREATE INDEX idx_shared_links_gasto ON shared_expense_links(gasto_id)",
        "CREATE INDEX idx_settlements_household ON household_settlements(household_id)",
        "CREATE INDEX idx_settlements_fecha ON household_settlements(household_id, fecha)",
        "CREATE INDEX idx_audit_log_household ON household_audit_log(household_id)",
    ]:
        db.execute(stmt)


def down(db):
    for table in [
        "household_audit_log", "household_settlements",
        "shared_expense_links", "household_invitations",
        "household_members", "hogares",
    ]:
        db.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
```

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

Property-based testing is appropriate here because the core of this feature — membership conflict enforcement, balance computation, authorization ordering, pagination, and settlement arithmetic — all involve functions with clear input/output behavior and universal properties that hold across a wide input space. The property tests use `hypothesis` (Python's PBT library).

**Property Reflection — redundancy eliminated before writing:**
- 1.2 (admin role + active status) is subsumed by 1.1 (create-and-verify includes both checks). Dropped.
- 1.6 (ValidationError for bad name) is subsumed by 1.5 (name validation property). Dropped.
- 2.6 + 2.7 are combined into a single revocation property.
- 4.2 (NotFoundError) is a single edge case, not universal — kept as example, not property.
- 5.1 + 5.2 (feed ordering + content) combined into one feed invariant property.
- 6.1 + 6.2 + 6.3 (balance computation logic) combined into the zero-sum balance invariant.
- 10.4 is covered by Property 8 (authz check ordering / 4.3). Dropped as duplicate.

---

### Property 1: Single active household membership

*For any* `familia_id` that is already an active member of a Household, any call to `create_household()` or `accept_invitation()` that would add them to a second Household SHALL return `HouseholdConflictError`, leaving all existing records unchanged.

**Validates: Requirements 1.3, 1.4, 2.5**

---

### Property 2: Membership conflict check precedes name validation

*For any* `familia_id` that is already an active member of a Household, calling `create_household()` with an invalid display name (empty, whitespace-only, or length > 100 after trimming) SHALL return `HouseholdConflictError` — not `ValidationError`. The membership check must fire before the name check.

**Validates: Requirement 1.4**

---

### Property 3: Household name trimming and length enforcement

*For any* string submitted as a Household display name, if `name.strip()` is the empty string or has length > 100, `create_household()` SHALL return `ValidationError`. If `name.strip()` is valid (1–100 chars), the stored name SHALL equal `name.strip()`, never the raw input.

**Validates: Requirements 1.5, 1.6**

---

### Property 4: Invitation token uniqueness and single-use enforcement

*For any* N invitations created across any set of Households, all N tokens SHALL be pairwise distinct. Furthermore, accepting a valid token SHALL mark it as `accepted`, and any subsequent attempt to accept the same token SHALL return `InvalidInvitationError` without creating a new membership.

**Validates: Requirements 2.1, 2.3**

---

### Property 5: Active invitation limit per Household

*For any* Household, after exactly 10 active (pending, non-expired, non-accepted, non-revoked) invitations have been created, any additional invitation creation attempt SHALL return `InvitationLimitError` without creating a record. Accepted, expired, and revoked invitations SHALL NOT count toward this limit.

**Validates: Requirement 2.2**

---

### Property 6: Invalid token states always produce InvalidInvitationError

*For any* invitation token whose `status` is `accepted`, `revoked`, or `expired` (or whose `expires_at` is in the past), calling `accept_invitation()` SHALL return `InvalidInvitationError` and SHALL NOT create any new `household_members` row.

**Validates: Requirement 2.4**

---

### Property 7: Non-admin leave atomicity — membership and links removed together

*For any* non-admin Household member who has shared N ≥ 0 expenses with the Household, calling `leave_household()` SHALL result in: (a) zero `household_members` rows for that `familia_id` in that Household, (b) zero `shared_expense_links` rows for that `familia_id` in that Household, and (c) the original `expenses` rows for that `familia_id` still existing with unchanged data. Settlements are not deleted.

**Validates: Requirements 3.1, 3.5**

---

### Property 8: Authorization check on shared_expense_link precedes duplicate check

*For any* `(gasto_id, household_id)` pair that already has an active `shared_expense_link`, if a different `familia_id` (one that does NOT own the expense) attempts to create a link for the same pair, the result SHALL be `UnauthorizedError` — not `DuplicateLinkError`. The ownership check fires first.

**Validates: Requirements 4.3, 10.4**

---

### Property 9: Shared expense link round-trip — original gasto is never mutated

*For any* valid `(gasto_id, household_id, familia_id)` triple where `gasto.familia_id == familia_id`, creating a `shared_expense_link` SHALL produce exactly one new link row and leave all fields of the original `expenses` row identical to their pre-link values. Deleting the link SHALL remove the link row and still leave the `expenses` row identical.

**Validates: Requirements 4.1, 4.5**

---

### Property 10: Idempotent duplicate link detection

*For any* valid `(gasto_id, household_id)` pair where an active `shared_expense_link` already exists, any subsequent `create_link()` call by the same owning `familia_id` SHALL return `DuplicateLinkError` without creating a second link row. The count of links for that pair SHALL remain exactly 1.

**Validates: Requirement 4.4**

---

### Property 11: Expense feed is always ordered by fecha descending

*For any* set of N shared expenses in a Household whose `fecha` values are not all identical, the list returned by `get_expense_feed()` (with no date filter) SHALL be sorted by `fecha` in descending order, and the list SHALL contain exactly N items when pagination covers the full set.

**Validates: Requirements 5.1, 5.2**

---

### Property 12: Date range filter includes both bounds and excludes outside dates

*For any* date range `[start_date, end_date]` (both inclusive) applied to `get_expense_feed()`, every returned item SHALL have `start_date <= item.fecha <= end_date`, and every shared expense with `fecha < start_date` or `fecha > end_date` SHALL NOT appear in the result.

**Validates: Requirement 5.3**

---

### Property 13: Pagination correctness — total count is stable and pages partition the result

*For any* Household with N shared expenses matching a given filter, and any `page_size` in [1, 100], the `total_count` returned on every page SHALL equal N. The union of all pages (page=1…ceil(N/page_size)) SHALL contain each of the N items exactly once, in the same relative order as an unpaginated result.

**Validates: Requirement 5.4**

---

### Property 14: Invalid date range returns ValidationError before any query

*For any* `(start_date, end_date)` pair where `start_date > end_date`, both `get_expense_feed()` and `compute_balance()` SHALL return `ValidationError` without executing any database query (verified by asserting no additional DB rows were read in the session).

**Validates: Requirements 5.7, 6.7**

---

### Property 15: Balance zero-sum invariant (the core financial property)

*For any* Household and any time period (or all-time), the sum of all members' `net_balance` values in the `MemberBalance` list returned by `compute_balance()` SHALL equal exactly `Decimal("0.00")`. This invariant must hold regardless of how many members, how many shared expenses, and how many settlements exist. No intermediate `float` value may appear anywhere in the computation.

**Validates: Requirements 6.1, 6.2, 6.3, 6.4**

---

### Property 16: Settlement adjusts payer and recipient balances by the settlement amount

*For any* valid settlement of `monto` from payer P to recipient R in a Household, the `net_balance` of P in a subsequent `compute_balance()` call SHALL be exactly `monto` higher than it was before the settlement was recorded, and the `net_balance` of R SHALL be exactly `monto` lower. The zero-sum invariant (Property 15) SHALL still hold.

**Validates: Requirement 6.4, 7.1**

---

### Property 17: Settlement authorization — authenticated family must be the payer

*For any* household operation where the authenticated `familia_id` does not equal the `payer_familia_id` supplied to `record_settlement()`, the result SHALL be `UnauthorizedError` and no `household_settlements` row SHALL be created.

**Validates: Requirement 7.2**

---

### Property 18: Self-settlement is always rejected

*For any* `familia_id`, calling `record_settlement()` with `payer_familia_id == recipient_familia_id` SHALL return `ValidationError` regardless of the amount, date, or household membership status.

**Validates: Requirement 7.4**

---

### Property 19: Non-positive settlement amount is always rejected

*For any* `monto` where `monto <= Decimal("0")` (including zero and any negative Decimal), `record_settlement()` SHALL return `ValidationError` without creating any record.

**Validates: Requirement 7.5**

---

### Property 20: Audit log completeness — every link mutation is logged

*For any* sequence of `create_link()` and `delete_link()` calls on any `(gasto_id, household_id, familia_id)` triple, the `household_audit_log` table SHALL contain exactly one entry per call, with the correct `action` (`"created"` or `"deleted"`), matching `familia_id`, `gasto_id`, `household_id`, and a `timestamp` within a reasonable window of the call time. No call creates more than one audit entry.

**Validates: Requirement 10.5**

---

### Property 21: Household query isolation — only linked expenses appear in feed

*For any* `expenses` row that belongs to a member's `familia_id` but has NO corresponding `shared_expense_link` for the target `household_id`, that expense SHALL NOT appear in the result of `get_expense_feed()` for that Household, regardless of any other matching filter criteria.

**Validates: Requirements 10.1, 10.2**

---

## Error Handling

### Ordering guarantees

The service layer enforces a strict check ordering that matches the requirements. This is not left to convention — each service method documents the order explicitly in its docstring:

| Service method | Check order |
|---|---|
| `HouseholdService.create_household()` | 1. Membership conflict → 2. Name validation → 3. DB write |
| `InvitationService.accept_invitation()` | 1. Token validity → 2. Membership conflict → 3. DB write |
| `ExpenseSharingService.create_link()` | 1. Caller membership → 2. Expense exists → 3. Ownership authz → 4. Duplicate check → 5. DB write |
| `SettlementService.record_settlement()` | 1. Authz (caller == payer) → 2. Self-settlement → 3. Amount > 0 → 4. Both members active → 5. DB write |

### Atomic operations

Three operations require atomic execution (all-or-nothing). The service layer wraps them in a single `session.flush()` inside the UnitOfWork. On exception, the UnitOfWork's context manager rolls back the entire transaction:

1. `HouseholdService.leave_household()` (non-admin): `DELETE household_members` + `DELETE shared_expense_links` in same transaction.
2. `HouseholdService.leave_household()` (admin-only disband): `UPDATE hogares SET status=disbanded` + `DELETE household_members` + `DELETE shared_expense_links` in same transaction.
3. `ExpenseSharingService.create_expense_and_link()`: `INSERT expenses` + `INSERT shared_expense_links` in same transaction.

### `UnauthorizedError` response contract

When `UnauthorizedError` is returned from any feed or read operation, the controller returns it as `Err(UnauthorizedError(...))` — the `Ok` branch is never reached and no data structure (not even an empty list) is included in the response. The UI renders an "access denied" message and hides all data widgets.

### Error propagation to UI

The `HouseholdController` returns `Result[T, AppError]`. The view layer pattern-matches:

```python
match result:
    case Ok(data):
        self._render(data)
    case Err(UnauthorizedError()):
        self._show_access_denied()
    case Err(HouseholdConflictError(message)):
        self._show_conflict_error(message)
    case Err(error):
        self._show_generic_error(error.message)
```

---

## Testing Strategy

### Dual Testing Approach

Unit tests cover specific examples, edge cases, and error ordering conditions. Property tests verify universal invariants across randomly generated inputs using `hypothesis`.

### Property-Based Testing Setup

Library: `hypothesis` (already in Python ecosystem; add to `pyproject.toml` dev dependencies).

```toml
[tool.pytest.ini_options]
# in pytest.ini or pyproject.toml
addopts = "--hypothesis-seed=0"

[dependency-groups]
dev = [
    "hypothesis>=6.100",
    # ... existing dev deps
]
```

Each property test:
- Runs a minimum of 100 examples (`@settings(max_examples=100)`).
- Uses `@given` with `hypothesis.strategies` to generate inputs.
- Is tagged with a comment referencing the design property: `# Feature: shared-household-expenses, Property N: <title>`.
- Uses real PostgreSQL with transaction rollback isolation (same pattern as existing tests in `tests/conftest.py`).

Example property test structure:

```python
# Feature: shared-household-expenses, Property 15: Balance zero-sum invariant
@given(
    expenses=st.lists(
        st.decimals(min_value=Decimal("0.01"), max_value=Decimal("9999.99"),
                    allow_nan=False, allow_infinity=False),
        min_size=1, max_size=20
    ),
    n_members=st.integers(min_value=2, max_value=5),
)
@settings(max_examples=100)
def test_balance_zero_sum_invariant(db_session, expenses, n_members):
    """
    For any set of shared expenses across N members, sum(net_balance) == Decimal("0.00").
    Property 15.
    """
    # Setup: create household with n_members, distribute expenses randomly
    # ...
    balances = balance_service.compute_balance(household_id, familia_id=members[0].familia_id)
    assert isinstance(balances, Ok)
    total = sum(b.net_balance for b in balances.ok())
    assert total == Decimal("0.00")
```

### Unit Test Coverage

| Test file | Key scenarios |
|---|---|
| `tests/test_household_service.py` | create, conflict check ordering, name trimming, leave (non-admin/admin/last-admin) |
| `tests/test_invitation_service.py` | create, limit enforcement, accept, revoke, expired token handling |
| `tests/test_expense_sharing_service.py` | create_link authz ordering, duplicate detection, atomic create-and-share |
| `tests/test_household_balance_service.py` | zero-sum, Decimal-only arithmetic, period filter, settlements included |
| `tests/test_settlement_service.py` | authz, self-settlement, non-positive amount, event emission |
| `tests/test_household_repository.py` | inner join isolation, feed ordering, pagination |
| `tests/test_household_audit_log.py` | every link mutation writes audit entry |

### Integration Tests

- `tests/test_household_ai_context.py`: vector retrieval scoping for household vs. personal context (requires running Ollama or mocked embedding service).
- `tests/test_household_atomic_operations.py`: simulate DB failure mid-operation and verify rollback.

### What PBT is NOT used for

The following requirements use example-based or integration tests only, per the classification in the prework:

- Req 8 (UI rendering): manual / Flet component tests.
- Req 9 (AI vectorization): integration tests with mocked `EmbeddingService`.
- Req 3.1 (atomicity under failure): integration test with simulated exception injection.
- Req 4.7 (atomic create-and-share rollback): integration test.

---
