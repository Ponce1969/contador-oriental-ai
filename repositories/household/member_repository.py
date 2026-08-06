from __future__ import annotations

from sqlalchemy import select, delete, update
from sqlalchemy.orm import Session

from database.tables import HouseholdMemberTable, HogarTable
from models.household_model import HouseholdMember


class HouseholdMemberRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_active_membership(self, familia_id: int) -> HouseholdMember | None:
        """Returns the member record if the familia is currently in an active household."""
        stmt = (
            select(HouseholdMemberTable)
            .join(HogarTable, HogarTable.id == HouseholdMemberTable.household_id)
            .where(
                HouseholdMemberTable.familia_id == familia_id,
                HogarTable.status == "active",
            )
        )
        row = self.session.execute(stmt).scalar_one_or_none()
        if not row:
            return None
        return HouseholdMember(
            id=row.id,
            household_id=row.household_id,
            familia_id=row.familia_id,
            role=row.role,
            joined_at=row.joined_at,
        )

    def get_members(self, household_id: int) -> list[HouseholdMember]:
        stmt = select(HouseholdMemberTable).where(HouseholdMemberTable.household_id == household_id)
        rows = self.session.execute(stmt).scalars().all()
        return [
            HouseholdMember(
                id=r.id,
                household_id=r.household_id,
                familia_id=r.familia_id,
                role=r.role,
                joined_at=r.joined_at,
            )
            for r in rows
        ]

    def add_member(self, household_id: int, familia_id: int, role: str) -> HouseholdMember:
        member = HouseholdMemberTable(household_id=household_id, familia_id=familia_id, role=role)
        self.session.add(member)
        self.session.flush()
        return HouseholdMember(
            id=member.id,
            household_id=member.household_id,
            familia_id=member.familia_id,
            role=member.role,
            joined_at=member.joined_at,
        )

    def remove_member(self, household_id: int, familia_id: int) -> None:
        stmt = delete(HouseholdMemberTable).where(
            HouseholdMemberTable.household_id == household_id,
            HouseholdMemberTable.familia_id == familia_id,
        )
        self.session.execute(stmt)

    def is_active_member(self, household_id: int, familia_id: int) -> bool:
        stmt = select(HouseholdMemberTable.id).where(
            HouseholdMemberTable.household_id == household_id,
            HouseholdMemberTable.familia_id == familia_id,
        )
        return self.session.execute(stmt).scalar_one_or_none() is not None

    def get_member_role(self, household_id: int, familia_id: int) -> str | None:
        stmt = select(HouseholdMemberTable.role).where(
            HouseholdMemberTable.household_id == household_id,
            HouseholdMemberTable.familia_id == familia_id,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def update_role(self, household_id: int, familia_id: int, role: str) -> None:
        stmt = (
            update(HouseholdMemberTable)
            .where(
                HouseholdMemberTable.household_id == household_id,
                HouseholdMemberTable.familia_id == familia_id,
            )
            .values(role=role)
        )
        self.session.execute(stmt)
