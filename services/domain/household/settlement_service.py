from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from repositories.household.settlement_repository import HouseholdSettlementRepository
    from repositories.household.member_repository import HouseholdMemberRepository

from models.household_model import HouseholdSettlement
from models.errors import UnauthorizedError, ValidationError, NotAMemberError
# from core.events import event_system, EventType # We will use it later in the controller or inject it

class SettlementService:
    def __init__(
        self,
        settlement_repo: HouseholdSettlementRepository,
        member_repo: HouseholdMemberRepository,
    ) -> None:
        self.settlement_repo = settlement_repo
        self.member_repo = member_repo

    def record_settlement(
        self,
        household_id: int,
        authenticated_familia_id: int,
        payer_familia_id: int,
        recipient_familia_id: int,
        monto: Decimal,
        fecha: date,
    ) -> HouseholdSettlement:
        if authenticated_familia_id != payer_familia_id:
            raise UnauthorizedError("Solo podés registrar un pago si sos el pagador.")
            
        if payer_familia_id == recipient_familia_id:
            raise ValidationError("No podés registrar un pago a vos mismo.")
            
        if monto <= 0:
            raise ValidationError("El monto del pago debe ser mayor a 0.")
            
        if not self.member_repo.is_active_member(household_id, payer_familia_id):
            raise NotAMemberError("El pagador no es miembro del hogar.")
            
        if not self.member_repo.is_active_member(household_id, recipient_familia_id):
            raise NotAMemberError("El destinatario no es miembro del hogar.")
            
        return self.settlement_repo.create(
            household_id=household_id,
            payer_familia_id=payer_familia_id,
            recipient_familia_id=recipient_familia_id,
            monto=monto,
            fecha=fecha,
        )
