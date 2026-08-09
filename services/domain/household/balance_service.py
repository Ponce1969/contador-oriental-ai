from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from repositories.household.link_repository import SharedExpenseLinkRepository
    from repositories.household.settlement_repository import HouseholdSettlementRepository
    from repositories.household.member_repository import HouseholdMemberRepository

from models.household_model import MemberBalance
from models.errors import NotAMemberError
from database.tables import FamiliaTable
from sqlalchemy.orm import Session
from sqlalchemy import select

class HouseholdBalanceService:
    def __init__(
        self,
        link_repo: SharedExpenseLinkRepository,
        settlement_repo: HouseholdSettlementRepository,
        member_repo: HouseholdMemberRepository,
        session: Session,
    ) -> None:
        self.link_repo = link_repo
        self.settlement_repo = settlement_repo
        self.member_repo = member_repo
        self.session = session

    def compute_balance(
        self, 
        household_id: int, 
        caller_familia_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[MemberBalance]:
        if not self.member_repo.is_active_member(household_id, caller_familia_id):
            raise NotAMemberError("No sos miembro de este hogar.")
            
        members = self.member_repo.get_members(household_id)
        if not members:
            return []
            
        # Get names for display
        member_ids = [m.familia_id for m in members]
        familias = self.session.execute(
            select(FamiliaTable).where(FamiliaTable.id.in_(member_ids))
        ).scalars().all()
        names = {f.id: f.nombre for f in familias}
        
        # Per-currency contributions (multi-currency safe)
        contributions = self.link_repo.sum_contributions_per_member(household_id)
        settlements = self.settlement_repo.sum_per_member(household_id)

        # Group contributions by member, summing across currencies per member
        # (equal_share is currency-independent; net_balance inherits member totals)
        by_member: dict[int, Decimal] = {}
        for (fid, _ccy), amount in contributions.items():
            by_member[fid] = by_member.get(fid, Decimal("0")) + amount

        total_expense = sum(by_member.values())
        member_count = Decimal(len(members))
        equal_share = total_expense / member_count if member_count > 0 else Decimal("0")
        
        result: list[MemberBalance] = []
        for member in members:
            fid = member.familia_id
            contributed = by_member.get(fid, Decimal("0"))
            settlement_data = settlements.get(fid, {"paid": Decimal("0"), "received": Decimal("0")})
            
            # Net balance = (Equal Share) - (Contributed) - (Settlements Paid) + (Settlements Received)
            # Positive = owes money to the group
            # Negative = group owes money to this member
            
            net = equal_share - contributed - settlement_data["paid"] + settlement_data["received"]
            
            result.append(MemberBalance(
                familia_id=fid,
                familia_nombre=names.get(fid, f"Familia {fid}"),
                total_contributed=contributed,
                equal_share=equal_share,
                net_balance=net,
            ))
            
        return result
