from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from result import Err, Ok, Result

from controllers.base_controller import BaseController
from core.events import Event, EventType

from repositories.household.household_repository import HouseholdRepository
from repositories.household.member_repository import HouseholdMemberRepository
from repositories.household.invitation_repository import HouseholdInvitationRepository
from repositories.household.link_repository import SharedExpenseLinkRepository
from repositories.household.settlement_repository import HouseholdSettlementRepository
from repositories.household.audit_repository import HouseholdAuditLogRepository

from services.domain.household.household_service import HouseholdService
from services.domain.household.invitation_service import InvitationService
from services.domain.household.expense_sharing_service import ExpenseSharingService
from services.domain.household.balance_service import HouseholdBalanceService
from services.domain.household.settlement_service import SettlementService

from models.household_model import (
    Household, 
    HouseholdInvitation, 
    SharedExpenseLink, 
    MemberBalance, 
    HouseholdSettlement, 
    HouseholdMember,
    ExpenseFeedPage
)
from models.errors import AppError, UnauthorizedError

logger = logging.getLogger(__name__)

class HouseholdController(BaseController):
    def _ensure_familia_id(self) -> int:
        if not self._familia_id:
            raise UnauthorizedError("Usuario no autenticado.")
        return self._familia_id

    def get_title(self) -> str:
        return "Hogar Compartido"

    def create_household(self, nombre: str) -> Result[Household, Exception]:
        try:
            familia_id = self._ensure_familia_id()
            with self._get_session() as session:
                household_repo = HouseholdRepository(session)
                member_repo = HouseholdMemberRepository(session)
                link_repo = SharedExpenseLinkRepository(session)
                settlement_repo = HouseholdSettlementRepository(session)
                balance_service = HouseholdBalanceService(link_repo, settlement_repo, member_repo, session)
                service = HouseholdService(household_repo, member_repo, link_repo, balance_service)
                
                household = service.create_household(nombre, familia_id)
                session.commit()
                return Ok(household)
        except Exception as e:
            logger.error(f"[HouseholdController] create_household error: {e}")
            return Err(e)

    def get_current_household(self) -> Result[Household | None, Exception]:
        try:
            familia_id = self._ensure_familia_id()
            with self._get_session() as session:
                household_repo = HouseholdRepository(session)
                member_repo = HouseholdMemberRepository(session)
                link_repo = SharedExpenseLinkRepository(session)
                settlement_repo = HouseholdSettlementRepository(session)
                balance_service = HouseholdBalanceService(link_repo, settlement_repo, member_repo, session)
                service = HouseholdService(household_repo, member_repo, link_repo, balance_service)
                
                household = service.get_household_for_familia(familia_id)
                return Ok(household)
        except Exception as e:
            logger.error(f"[HouseholdController] get_current_household error: {e}")
            return Err(e)

    def leave_household(self) -> Result[None, Exception]:
        try:
            familia_id = self._ensure_familia_id()
            with self._get_session() as session:
                household_repo = HouseholdRepository(session)
                member_repo = HouseholdMemberRepository(session)
                link_repo = SharedExpenseLinkRepository(session)
                settlement_repo = HouseholdSettlementRepository(session)
                balance_service = HouseholdBalanceService(link_repo, settlement_repo, member_repo, session)
                service = HouseholdService(household_repo, member_repo, link_repo, balance_service)
                
                household = service.get_household_for_familia(familia_id)
                if household:
                    service.leave_household(household.id, familia_id)
                    session.commit()
                return Ok(None)
        except Exception as e:
            logger.error(f"[HouseholdController] leave_household error: {e}")
            return Err(e)

    def transfer_admin(self, to_familia_id: int) -> Result[None, Exception]:
        try:
            familia_id = self._ensure_familia_id()
            with self._get_session() as session:
                household_repo = HouseholdRepository(session)
                member_repo = HouseholdMemberRepository(session)
                link_repo = SharedExpenseLinkRepository(session)
                settlement_repo = HouseholdSettlementRepository(session)
                balance_service = HouseholdBalanceService(link_repo, settlement_repo, member_repo, session)
                service = HouseholdService(household_repo, member_repo, link_repo, balance_service)
                
                household = service.get_household_for_familia(familia_id)
                if household:
                    service.transfer_admin(household.id, familia_id, to_familia_id)
                    session.commit()
                return Ok(None)
        except Exception as e:
            logger.error(f"[HouseholdController] transfer_admin error: {e}")
            return Err(e)

    def create_invitation(self) -> Result[HouseholdInvitation, Exception]:
        try:
            familia_id = self._ensure_familia_id()
            with self._get_session() as session:
                invitation_repo = HouseholdInvitationRepository(session)
                member_repo = HouseholdMemberRepository(session)
                household_repo = HouseholdRepository(session)
                
                membership = member_repo.get_active_membership(familia_id)
                if not membership:
                    raise AppError("No sos miembro de un hogar activo.")
                    
                service = InvitationService(invitation_repo, member_repo)
                inv = service.create_invitation(membership.household_id, familia_id)
                session.commit()
                return Ok(inv)
        except Exception as e:
            logger.error(f"[HouseholdController] create_invitation error: {e}")
            return Err(e)

    def accept_invitation(self, token: str) -> Result[None, Exception]:
        try:
            familia_id = self._ensure_familia_id()
            with self._get_session() as session:
                invitation_repo = HouseholdInvitationRepository(session)
                member_repo = HouseholdMemberRepository(session)
                
                service = InvitationService(invitation_repo, member_repo)
                service.accept_invitation(token, familia_id)
                session.commit()
                
                # Emit event if needed later
                return Ok(None)
        except Exception as e:
            logger.error(f"[HouseholdController] accept_invitation error: {e}")
            return Err(e)

    def revoke_invitation(self, token: str) -> Result[None, Exception]:
        try:
            familia_id = self._ensure_familia_id()
            with self._get_session() as session:
                invitation_repo = HouseholdInvitationRepository(session)
                member_repo = HouseholdMemberRepository(session)
                
                membership = member_repo.get_active_membership(familia_id)
                if not membership:
                    raise AppError("No sos miembro de un hogar activo.")
                    
                service = InvitationService(invitation_repo, member_repo)
                service.revoke_invitation(membership.household_id, token, familia_id)
                session.commit()
                return Ok(None)
        except Exception as e:
            logger.error(f"[HouseholdController] revoke_invitation error: {e}")
            return Err(e)

    def share_expense(self, gasto_id: int) -> Result[SharedExpenseLink, Exception]:
        try:
            familia_id = self._ensure_familia_id()
            with self._get_session() as session:
                member_repo = HouseholdMemberRepository(session)
                link_repo = SharedExpenseLinkRepository(session)
                audit_repo = HouseholdAuditLogRepository(session)
                
                membership = member_repo.get_active_membership(familia_id)
                if not membership:
                    raise AppError("No sos miembro de un hogar activo.")
                    
                service = ExpenseSharingService(link_repo, member_repo, audit_repo, session)
                link = service.create_link(membership.household_id, gasto_id, familia_id)
                session.commit()
                
                self._event_system.fire_and_forget(
                    Event(
                        type=EventType.SHARED_EXPENSE_LINK_CREADO,
                        payload={
                            "household_id": membership.household_id,
                            "gasto_id": gasto_id,
                            "familia_id": familia_id,
                        },
                    )
                )
                return Ok(link)
        except Exception as e:
            logger.error(f"[HouseholdController] share_expense error: {e}")
            return Err(e)

    def unshare_expense(self, gasto_id: int) -> Result[None, Exception]:
        try:
            familia_id = self._ensure_familia_id()
            with self._get_session() as session:
                member_repo = HouseholdMemberRepository(session)
                link_repo = SharedExpenseLinkRepository(session)
                audit_repo = HouseholdAuditLogRepository(session)
                
                membership = member_repo.get_active_membership(familia_id)
                if not membership:
                    raise AppError("No sos miembro de un hogar activo.")
                    
                service = ExpenseSharingService(link_repo, member_repo, audit_repo, session)
                service.delete_link(membership.household_id, gasto_id, familia_id)
                session.commit()
                
                self._event_system.fire_and_forget(
                    Event(
                        type=EventType.SHARED_EXPENSE_LINK_ELIMINADO,
                        payload={
                            "household_id": membership.household_id,
                            "gasto_id": gasto_id,
                            "familia_id": familia_id,
                        },
                    )
                )
                return Ok(None)
        except Exception as e:
            logger.error(f"[HouseholdController] unshare_expense error: {e}")
            return Err(e)

    def get_expense_feed(
        self, page: int = 1, page_size: int = 20, filter_familia_id: int | None = None
    ) -> Result[ExpenseFeedPage, Exception]:
        try:
            familia_id = self._ensure_familia_id()
            with self._get_session() as session:
                member_repo = HouseholdMemberRepository(session)
                link_repo = SharedExpenseLinkRepository(session)
                
                membership = member_repo.get_active_membership(familia_id)
                if not membership:
                    return Ok(ExpenseFeedPage(items=[], total=0, page=page, pages=0))
                    
                feed = link_repo.get_feed_for_household(
                    household_id=membership.household_id,
                    page=page,
                    page_size=page_size,
                    filter_familia_id=filter_familia_id
                )
                return Ok(feed)
        except Exception as e:
            logger.error(f"[HouseholdController] get_expense_feed error: {e}")
            return Err(e)

    def get_balance(
        self, start_date: str | None = None, end_date: str | None = None
    ) -> Result[list[MemberBalance], Exception]:
        try:
            familia_id = self._ensure_familia_id()
            with self._get_session() as session:
                member_repo = HouseholdMemberRepository(session)
                link_repo = SharedExpenseLinkRepository(session)
                settlement_repo = HouseholdSettlementRepository(session)
                
                membership = member_repo.get_active_membership(familia_id)
                if not membership:
                    return Ok([])
                    
                service = HouseholdBalanceService(link_repo, settlement_repo, member_repo, session)
                balances = service.compute_balance(
                    membership.household_id, familia_id, start_date, end_date
                )
                return Ok(balances)
        except Exception as e:
            logger.error(f"[HouseholdController] get_balance error: {e}")
            return Err(e)

    def record_settlement(
        self, recipient_familia_id: int, monto: Decimal, fecha: date
    ) -> Result[HouseholdSettlement, Exception]:
        try:
            familia_id = self._ensure_familia_id()
            with self._get_session() as session:
                member_repo = HouseholdMemberRepository(session)
                settlement_repo = HouseholdSettlementRepository(session)
                
                membership = member_repo.get_active_membership(familia_id)
                if not membership:
                    raise AppError("No sos miembro de un hogar activo.")
                    
                service = SettlementService(settlement_repo, member_repo)
                settlement = service.record_settlement(
                    household_id=membership.household_id,
                    authenticated_familia_id=familia_id,
                    payer_familia_id=familia_id,
                    recipient_familia_id=recipient_familia_id,
                    monto=monto,
                    fecha=fecha
                )
                session.commit()
                
                self._event_system.fire_and_forget(
                    Event(
                        type=EventType.SETTLEMENT_CREADO,
                        payload={
                            "household_id": membership.household_id,
                            "payer_familia_id": familia_id,
                            "recipient_familia_id": recipient_familia_id,
                            "monto": float(monto),
                        },
                    )
                )
                
                return Ok(settlement)
        except Exception as e:
            logger.error(f"[HouseholdController] record_settlement error: {e}")
            return Err(e)

    def get_members(self) -> Result[list[HouseholdMember], Exception]:
        try:
            familia_id = self._ensure_familia_id()
            with self._get_session() as session:
                member_repo = HouseholdMemberRepository(session)
                membership = member_repo.get_active_membership(familia_id)
                if not membership:
                    return Ok([])
                members = member_repo.get_members(membership.household_id)
                return Ok(members)
        except Exception as e:
            logger.error(f"[HouseholdController] get_members error: {e}")
            return Err(e)
