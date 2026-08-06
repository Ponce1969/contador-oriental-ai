from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppError(Exception):
    message: str


@dataclass(frozen=True)
class DatabaseError(AppError):
    pass


@dataclass(frozen=True)
class ValidationError(AppError):
    pass


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
