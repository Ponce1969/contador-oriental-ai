from __future__ import annotations

from sqlalchemy import update
from sqlalchemy.orm import Session

from database.tables import HogarTable
from models.household_model import Household


class HouseholdRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, nombre: str) -> Household:
        hogar = HogarTable(nombre=nombre)
        self.session.add(hogar)
        self.session.flush()
        return Household(
            id=hogar.id,
            nombre=hogar.nombre,
            status=hogar.status,
            created_at=hogar.created_at,
        )

    def get_by_id(self, household_id: int) -> Household | None:
        hogar = self.session.get(HogarTable, household_id)
        if not hogar:
            return None
        return Household(
            id=hogar.id,
            nombre=hogar.nombre,
            status=hogar.status,
            created_at=hogar.created_at,
        )

    def set_disbanded(self, household_id: int) -> None:
        self.session.execute(
            update(HogarTable)
            .where(HogarTable.id == household_id)
            .values(status="disbanded")
        )
