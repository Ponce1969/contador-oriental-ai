from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from repositories.household.invitation_repository import HouseholdInvitationRepository
from repositories.household.member_repository import HouseholdMemberRepository
from models.household_model import HouseholdInvitation
from models.errors import (
    UnauthorizedError, 
    HouseholdConflictError, 
    InvalidInvitationError, 
    InvitationLimitError
)

class InvitationService:
    def __init__(
        self,
        invitation_repo: HouseholdInvitationRepository,
        member_repo: HouseholdMemberRepository,
    ) -> None:
        self.invitation_repo = invitation_repo
        self.member_repo = member_repo

    def create_invitation(self, household_id: int, caller_familia_id: int) -> HouseholdInvitation:
        role = self.member_repo.get_member_role(household_id, caller_familia_id)
        if role != "admin":
            raise UnauthorizedError("Solo un administrador puede crear invitaciones.")
        
        active_count = self.invitation_repo.count_active(household_id)
        if active_count >= 10:
            raise InvitationLimitError("No se pueden tener más de 10 invitaciones activas simultáneamente.")
            
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=48)
        
        return self.invitation_repo.create(household_id, token, expires_at)

    def accept_invitation(self, token: str, joiner_familia_id: int) -> None:
        invitation = self.invitation_repo.get_by_token(token)
        if not invitation:
            raise InvalidInvitationError("El link de invitación no existe.")
            
        if invitation.status != "pending" or invitation.expires_at < datetime.now():
            raise InvalidInvitationError("El link de invitación ha expirado o ya fue utilizado.")
            
        active_member = self.member_repo.get_active_membership(joiner_familia_id)
        if active_member:
            raise HouseholdConflictError("Ya pertenecés a un hogar activo.")
            
        self.member_repo.add_member(invitation.household_id, joiner_familia_id, role="member")
        self.invitation_repo.mark_accepted(token, joiner_familia_id)

    def revoke_invitation(self, household_id: int, token: str, caller_familia_id: int) -> None:
        role = self.member_repo.get_member_role(household_id, caller_familia_id)
        if role != "admin":
            raise UnauthorizedError("Solo un administrador puede revocar invitaciones.")
            
        invitation = self.invitation_repo.get_by_token(token)
        if not invitation or invitation.household_id != household_id:
            raise InvalidInvitationError("Invitación no encontrada.")
            
        if invitation.status == "accepted":
            raise InvalidInvitationError("No se puede revocar una invitación que ya fue aceptada.")
            
        if invitation.status == "pending":
            self.invitation_repo.mark_revoked(token)
