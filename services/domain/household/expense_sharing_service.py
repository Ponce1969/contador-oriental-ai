from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from repositories.household.audit_repository import HouseholdAuditLogRepository
    from repositories.household.link_repository import SharedExpenseLinkRepository
    from repositories.household.member_repository import HouseholdMemberRepository

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.tables import ExpenseTable
from models.errors import (
    DuplicateLinkError,
    NotAMemberError,
    NotFoundError,
    UnauthorizedError,
)
from models.household_model import SharedExpenseLink


class ExpenseSharingService:
    def __init__(
        self,
        link_repo: SharedExpenseLinkRepository,
        member_repo: HouseholdMemberRepository,
        audit_repo: HouseholdAuditLogRepository,
        session: Session,
    ) -> None:
        self.link_repo = link_repo
        self.member_repo = member_repo
        self.audit_repo = audit_repo
        self.session = session

    def create_link(self, household_id: int, gasto_id: int, caller_familia_id: int) -> SharedExpenseLink:
        if not self.member_repo.is_active_member(household_id, caller_familia_id):
            raise NotAMemberError("No sos miembro de este hogar.")
            
        gasto = self.session.execute(
            select(ExpenseTable).where(ExpenseTable.id == gasto_id)
        ).scalar_one_or_none()
        
        if not gasto:
            raise NotFoundError("El gasto no existe.")
            
        if gasto.familia_id != caller_familia_id:
            raise UnauthorizedError("Solo el dueño del gasto puede compartirlo.")
            
        existing = self.link_repo.get_by_gasto_and_household(gasto_id, household_id)
        if existing:
            raise DuplicateLinkError("El gasto ya está compartido en este hogar.")
            
        link = self.link_repo.create(household_id, gasto_id, caller_familia_id)
        self.audit_repo.append(household_id, caller_familia_id, gasto_id, action="created")
        return link

    def delete_link(self, household_id: int, gasto_id: int, caller_familia_id: int) -> None:
        if not self.member_repo.is_active_member(household_id, caller_familia_id):
            raise NotAMemberError("No sos miembro de este hogar.")
            
        existing = self.link_repo.get_by_gasto_and_household(gasto_id, household_id)
        if not existing:
            raise NotFoundError("El gasto no está compartido en este hogar.")
            
        if existing.familia_id != caller_familia_id:
            raise UnauthorizedError("Solo el usuario que compartió el gasto puede descompartirlo.")
            
        self.link_repo.delete_by_gasto_and_household(gasto_id, household_id)
        self.audit_repo.append(household_id, caller_familia_id, gasto_id, action="deleted")

    def create_expense_and_link(self, household_id: int, expense_data: dict, caller_familia_id: int) -> tuple[ExpenseTable, SharedExpenseLink]:
        if not self.member_repo.is_active_member(household_id, caller_familia_id):
            raise NotAMemberError("No sos miembro de este hogar.")
            
        try:
            # Atomic insertion of expense and link
            expense = ExpenseTable(**expense_data)
            expense.familia_id = caller_familia_id
            self.session.add(expense)
            self.session.flush() # get expense.id
            
            link = self.link_repo.create(household_id, expense.id, caller_familia_id)
            self.audit_repo.append(household_id, caller_familia_id, expense.id, action="created")
            
            return expense, link
        except Exception as e:
            # Rolled back in controller session context
            raise e
