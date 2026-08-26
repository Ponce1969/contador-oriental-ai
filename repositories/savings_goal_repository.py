"""
Repositorio para operaciones de persistencia de Metas de Ahorro y Contribuciones.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.tables import SavingsGoalContributionTable, SavingsGoalTable
from models.savings_goal_model import (
    ContributionSource,
    GoalCategory,
    GoalContribution,
    SavingsGoal,
)
from repositories.base_table_repository import BaseTableRepository


class SavingsGoalRepository(BaseTableRepository[SavingsGoal, SavingsGoalTable]):
    """Repositorio para Metas de Ahorro con aislamiento por familia_id."""

    def __init__(self, session: Session, familia_id: int | None = None) -> None:
        super().__init__(session, SavingsGoalTable, familia_id)

    def _to_domain(self, table_row: SavingsGoalTable) -> SavingsGoal:
        return SavingsGoal(
            id=table_row.id,
            familia_id=table_row.familia_id,
            name=table_row.name,
            target_amount=table_row.target_amount,
            currency=table_row.currency,
            current_amount=table_row.current_amount,
            deadline=table_row.deadline,
            category=GoalCategory(table_row.category)
            if table_row.category in GoalCategory._value2member_map_
            else GoalCategory.GENERAL,
            icon=table_row.icon,
            color=table_row.color,
            is_completed=table_row.is_completed,
            created_at=table_row.created_at,
            updated_at=table_row.updated_at,
        )

    def _to_table(self, entity: SavingsGoal) -> SavingsGoalTable:
        return SavingsGoalTable(
            id=entity.id if entity.id is not None else None,
            familia_id=entity.familia_id,
            name=entity.name,
            target_amount=entity.target_amount,
            currency=entity.currency,
            current_amount=entity.current_amount,
            deadline=entity.deadline,
            category=entity.category.value,
            icon=entity.icon,
            color=entity.color,
            is_completed=entity.is_completed,
        )

    def _update_specific_fields(
        self, table_row: SavingsGoalTable, entity: SavingsGoal
    ) -> None:
        table_row.name = entity.name
        table_row.target_amount = entity.target_amount
        table_row.currency = entity.currency
        table_row.current_amount = entity.current_amount
        table_row.deadline = entity.deadline
        table_row.category = entity.category.value
        table_row.icon = entity.icon
        table_row.color = entity.color
        table_row.is_completed = entity.is_completed

    def list_active(self) -> Sequence[SavingsGoal]:
        """Retorna todas las metas no completadas de la familia."""
        stmt = select(SavingsGoalTable).where(SavingsGoalTable.is_completed.is_(False))
        stmt = self._filter_by_family(stmt)
        rows = self.session.scalars(stmt).all()
        return [self._to_domain(r) for r in rows]

    def update_current_amount(
        self, goal_id: int, new_amount: Decimal, is_completed: bool = False
    ) -> bool:
        """Actualiza el monto ahorrado y estado de una meta."""
        stmt = select(SavingsGoalTable).where(SavingsGoalTable.id == goal_id)
        stmt = self._filter_by_family(stmt)
        row = self.session.scalars(stmt).first()
        if not row:
            return False
        row.current_amount = new_amount
        row.is_completed = is_completed
        self.session.flush()
        return True


class GoalContributionRepository(
    BaseTableRepository[GoalContribution, SavingsGoalContributionTable]
):
    """Repositorio para Aportes a Metas de Ahorro."""

    def __init__(self, session: Session, familia_id: int | None = None) -> None:
        super().__init__(session, SavingsGoalContributionTable, familia_id)

    def _to_domain(self, table_row: SavingsGoalContributionTable) -> GoalContribution:
        return GoalContribution(
            id=table_row.id,
            savings_goal_id=table_row.savings_goal_id,
            family_member_id=table_row.family_member_id,
            amount=table_row.amount,
            currency=table_row.currency,
            source_type=ContributionSource(table_row.source_type)
            if table_row.source_type in ContributionSource._value2member_map_
            else ContributionSource.REGULAR_INCOME,
            note=table_row.note,
            fecha=table_row.fecha,
            created_at=table_row.created_at,
        )

    def _to_table(self, entity: GoalContribution) -> SavingsGoalContributionTable:
        return SavingsGoalContributionTable(
            id=entity.id if entity.id is not None else None,
            savings_goal_id=entity.savings_goal_id,
            family_member_id=entity.family_member_id,
            amount=entity.amount,
            currency=entity.currency,
            source_type=entity.source_type.value,
            note=entity.note,
            fecha=entity.fecha,
        )

    def list_by_goal_id(self, goal_id: int) -> list[GoalContribution]:
        """Retorna todos los aportes realizados a una meta."""
        stmt = (
            select(SavingsGoalContributionTable)
            .where(SavingsGoalContributionTable.savings_goal_id == goal_id)
            .order_by(SavingsGoalContributionTable.fecha.desc())
        )
        rows = self.session.scalars(stmt).all()
        return [self._to_domain(r) for r in rows]
