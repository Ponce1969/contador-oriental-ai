from __future__ import annotations

from sqlalchemy.orm import Session

from database.tables import HouseholdAuditLogTable


class HouseholdAuditLogRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def append(
        self, household_id: int, familia_id: int, gasto_id: int, action: str
    ) -> None:
        log = HouseholdAuditLogTable(
            household_id=household_id,
            familia_id=familia_id,
            gasto_id=gasto_id,
            action=action,
        )
        self.session.add(log)
        self.session.flush()
