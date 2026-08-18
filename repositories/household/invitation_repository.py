from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from database.tables import HouseholdInvitationTable
from models.household_model import HouseholdInvitation


class HouseholdInvitationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, household_id: int, token: str, expires_at: datetime) -> HouseholdInvitation:
        inv = HouseholdInvitationTable(household_id=household_id, token=token, expires_at=expires_at)
        self.session.add(inv)
        self.session.flush()
        return HouseholdInvitation(
            id=inv.id,
            household_id=inv.household_id,
            token=inv.token,
            status=inv.status,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
        )

    def get_by_token(self, token: str) -> HouseholdInvitation | None:
        inv = self.session.execute(
            select(HouseholdInvitationTable).where(HouseholdInvitationTable.token == token)
        ).scalar_one_or_none()
        
        if not inv:
            return None
            
        return HouseholdInvitation(
            id=inv.id,
            household_id=inv.household_id,
            token=inv.token,
            status=inv.status,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
        )

    def count_active(self, household_id: int) -> int:
        stmt = select(func.count(HouseholdInvitationTable.id)).where(
            HouseholdInvitationTable.household_id == household_id,
            HouseholdInvitationTable.status == "pending",
            HouseholdInvitationTable.expires_at > datetime.now(),
        )
        return self.session.execute(stmt).scalar_one() or 0

    def mark_accepted(self, token: str, familia_id: int) -> None:
        stmt = (
            update(HouseholdInvitationTable)
            .where(HouseholdInvitationTable.token == token)
            .values(status="accepted", accepted_by_familia_id=familia_id, accepted_at=datetime.now())
        )
        self.session.execute(stmt)

    def mark_revoked(self, token: str) -> None:
        stmt = (
            update(HouseholdInvitationTable)
            .where(HouseholdInvitationTable.token == token)
            .values(status="revoked")
        )
        self.session.execute(stmt)
