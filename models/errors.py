from __future__ import annotations


class AppError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message



class DatabaseError(AppError):
    pass



class ValidationError(AppError):
    pass



class NotFoundError(AppError):
    pass



class UnauthorizedError(AppError):
    pass



class HouseholdConflictError(AppError):
    """Raised when a familia is already an active member of a Household."""
    pass



class AdminMustTransferError(AppError):
    """Raised when an admin tries to leave a Household with other active members."""
    pass



class BalanceNotZeroError(AppError):
    """Raised when a member tries to leave a Household but their net balance is not zero."""
    pass



class NotAMemberError(AppError):
    """Raised when the familia is not an active member of the target Household."""
    pass



class InvalidInvitationError(AppError):
    """Raised when a token is expired, already accepted, or revoked."""
    pass



class InvitationLimitError(AppError):
    """Raised when the Household already has 10 active pending invitations."""
    pass



class DuplicateLinkError(AppError):
    """Raised when the (gasto_id, household_id) pair already has an active link."""
    pass
