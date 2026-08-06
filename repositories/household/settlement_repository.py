from __future__ import annotations

from datetime import date
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from database.tables import HouseholdSettlementTable
from models.household_model import HouseholdSettlement


class HouseholdSettlementRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        household_id: int,
        payer_familia_id: int,
        recipient_familia_id: int,
        monto: Decimal,
        fecha: date,
    ) -> HouseholdSettlement:
        settlement = HouseholdSettlementTable(
            household_id=household_id,
            payer_familia_id=payer_familia_id,
            recipient_familia_id=recipient_familia_id,
            monto=monto,
            fecha=fecha,
        )
        self.session.add(settlement)
        self.session.flush()
        return HouseholdSettlement(
            id=settlement.id,
            household_id=settlement.household_id,
            payer_familia_id=settlement.payer_familia_id,
            recipient_familia_id=settlement.recipient_familia_id,
            monto=settlement.monto,
            fecha=settlement.fecha,
            created_at=settlement.created_at,
        )

    def sum_per_member(self, household_id: int) -> dict[int, dict[str, Decimal]]:
        """
        Returns {familia_id: {"paid": Decimal, "received": Decimal}}
        """
        stmt_paid = (
            select(
                HouseholdSettlementTable.payer_familia_id,
                func.sum(HouseholdSettlementTable.monto),
            )
            .where(HouseholdSettlementTable.household_id == household_id)
            .group_by(HouseholdSettlementTable.payer_familia_id)
        )
        paid_rows = self.session.execute(stmt_paid).all()

        stmt_received = (
            select(
                HouseholdSettlementTable.recipient_familia_id,
                func.sum(HouseholdSettlementTable.monto),
            )
            .where(HouseholdSettlementTable.household_id == household_id)
            .group_by(HouseholdSettlementTable.recipient_familia_id)
        )
        received_rows = self.session.execute(stmt_received).all()

        result: dict[int, dict[str, Decimal]] = {}
        for r in paid_rows:
            fid = r[0]
            val = Decimal(r[1]) if r[1] else Decimal("0")
            if fid not in result:
                result[fid] = {"paid": Decimal("0"), "received": Decimal("0")}
            result[fid]["paid"] = val

        for r in received_rows:
            fid = r[0]
            val = Decimal(r[1]) if r[1] else Decimal("0")
            if fid not in result:
                result[fid] = {"paid": Decimal("0"), "received": Decimal("0")}
            result[fid]["received"] = val

        return result
