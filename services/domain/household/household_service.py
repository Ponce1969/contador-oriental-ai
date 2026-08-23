from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.domain.household.balance_service import HouseholdBalanceService

from models.errors import (
    AdminMustTransferError,
    BalanceNotZeroError,
    HouseholdConflictError,
    NotAMemberError,
    ValidationError,
)
from models.household_model import Household
from repositories.household.household_repository import HouseholdRepository
from repositories.household.link_repository import SharedExpenseLinkRepository
from repositories.household.member_repository import HouseholdMemberRepository


class HouseholdService:
    def __init__(
        self,
        household_repo: HouseholdRepository,
        member_repo: HouseholdMemberRepository,
        link_repo: SharedExpenseLinkRepository,
        balance_service: HouseholdBalanceService,
    ) -> None:
        self.household_repo = household_repo
        self.member_repo = member_repo
        self.link_repo = link_repo
        self.balance_service = balance_service

    def create_household(self, nombre: str, creator_familia_id: int) -> Household:
        active_member = self.member_repo.get_active_membership(creator_familia_id)
        if active_member:
            raise HouseholdConflictError("La familia ya pertenece a un hogar activo.")

        nombre = nombre.strip()
        if not nombre:
            raise ValidationError("El nombre del hogar no puede estar vacío.")

        household = self.household_repo.create(nombre)
        if household.id is not None:
            self.member_repo.add_member(household.id, creator_familia_id, role="admin")
        return household

    def get_household_for_familia(self, familia_id: int) -> Household | None:
        membership = self.member_repo.get_active_membership(familia_id)
        if not membership:
            return None
        return self.household_repo.get_by_id(membership.household_id)

    def leave_household(self, household_id: int, familia_id: int) -> None:
        membership = self.member_repo.get_active_membership(familia_id)
        if not membership or membership.household_id != household_id:
            raise NotAMemberError("No sos miembro de este hogar.")

        all_members = self.member_repo.get_members(household_id)

        # Si hay más de un miembro, verificamos que no haya deudas
        if len(all_members) > 1:
            balances = self.balance_service.compute_balance(
                household_id, familia_id, None, None
            )
            my_balance = next((b for b in balances if b.familia_id == familia_id), None)
            if my_balance and my_balance.net_balance != 0:
                raise BalanceNotZeroError(
                    "Tenés un balance pendiente (deuda o te deben). "
                    "Debés saldar cuentas antes de salir."
                )

        if membership.role == "admin":
            if len(all_members) > 1:
                raise AdminMustTransferError(
                    "Sos el único admin pero hay más miembros. "
                    "Transferí el rol de administrador antes de salir."
                )

            self.household_repo.set_disbanded(household_id)
            self.member_repo.remove_member(household_id, familia_id)
            self.link_repo.delete_all_for_household(household_id)
        else:
            self.member_repo.remove_member(household_id, familia_id)
            self.link_repo.delete_all_for_member(household_id, familia_id)

    def transfer_admin(
        self, household_id: int, from_familia_id: int, to_familia_id: int
    ) -> None:
        from_role = self.member_repo.get_member_role(household_id, from_familia_id)
        if from_role != "admin":
            raise ValidationError("Solo un administrador puede transferir el rol.")
        if not self.member_repo.is_active_member(household_id, to_familia_id):
            raise NotAMemberError("El destinatario no es miembro de este hogar.")

        self.member_repo.update_role(household_id, from_familia_id, "member")
        self.member_repo.update_role(household_id, to_familia_id, "admin")
