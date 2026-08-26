"""
Servicio para la gestión y simulación de Metas de Ahorro Familiares (Savings Goals).
"""

from __future__ import annotations

import logging
import math
from datetime import date, datetime
from decimal import Decimal

from result import Err, Result
from sqlalchemy.orm import Session

from models.errors import DatabaseError, ValidationError
from models.savings_goal_model import (
    GoalContribution,
    GoalContributionCreate,
    GoalSimulationResult,
    SavingsGoal,
    SavingsGoalCreate,
    SavingsGoalUpdate,
)
from repositories.savings_goal_repository import (
    GoalContributionRepository,
    SavingsGoalRepository,
)

logger = logging.getLogger(__name__)


class SavingsGoalService:
    """Servicio de negocio para metas de ahorro y simulaciones de fondeo."""

    def __init__(self, session: Session, familia_id: int | None = None) -> None:
        self.session = session
        self.familia_id = familia_id
        self.goal_repo = SavingsGoalRepository(session, familia_id)
        self.contrib_repo = GoalContributionRepository(session, familia_id)

    def create_goal(
        self, dto: SavingsGoalCreate
    ) -> Result[SavingsGoal, ValidationError | DatabaseError]:
        """Crea una nueva meta de ahorro."""
        if dto.target_amount <= Decimal("0"):
            return Err(ValidationError("El monto objetivo debe ser mayor a cero."))
        if not dto.name.strip():
            return Err(ValidationError("El nombre de la meta es requerido."))

        goal = SavingsGoal(
            familia_id=self.familia_id or dto.familia_id,
            name=dto.name.strip(),
            target_amount=dto.target_amount,
            currency=dto.currency,
            current_amount=Decimal("0.00"),
            deadline=dto.deadline,
            category=dto.category,
            icon=dto.icon,
            color=dto.color,
            is_completed=False,
        )
        return self.goal_repo.add(goal)

    def update_goal(
        self, goal_id: int, dto: SavingsGoalUpdate
    ) -> Result[SavingsGoal, ValidationError | DatabaseError]:
        """Actualiza los datos configurables de una meta."""
        existing_res = self.goal_repo.get_by_id(goal_id)
        if existing_res.is_err() or not existing_res.ok():
            return Err(ValidationError("La meta de ahorro no existe."))

        existing = existing_res.ok()
        assert existing is not None

        if dto.name is not None:
            if not dto.name.strip():
                return Err(
                    ValidationError("El nombre de la meta no puede estar vacío.")
                )
            existing.name = dto.name.strip()
        if dto.target_amount is not None:
            if dto.target_amount <= Decimal("0"):
                return Err(ValidationError("El monto objetivo debe ser mayor a cero."))
            existing.target_amount = dto.target_amount
            # Reevaluar si se completó
            existing.is_completed = existing.current_amount >= existing.target_amount
        if dto.currency is not None:
            existing.currency = dto.currency
        if dto.deadline is not None:
            existing.deadline = dto.deadline
        if dto.category is not None:
            existing.category = dto.category
        if dto.icon is not None:
            existing.icon = dto.icon
        if dto.color is not None:
            existing.color = dto.color
        if dto.is_completed is not None:
            existing.is_completed = dto.is_completed

        existing.updated_at = datetime.now()
        return self.goal_repo.update(existing)

    def delete_goal(self, goal_id: int) -> Result[bool, DatabaseError]:
        """Elimina una meta y sus aportes asociados."""
        return self.goal_repo.delete(goal_id)

    def get_goal(self, goal_id: int) -> Result[SavingsGoal, DatabaseError]:
        """Obtiene una meta por su ID."""
        return self.goal_repo.get_by_id(goal_id)

    def list_goals(self, active_only: bool = False) -> list[SavingsGoal]:
        """Lista las metas de la familia."""
        if active_only:
            return list(self.goal_repo.list_active())
        return list(self.goal_repo.get_all())

    def add_contribution(
        self, dto: GoalContributionCreate
    ) -> Result[GoalContribution, ValidationError | DatabaseError]:
        """Registra un aporte hacia una meta y actualiza el monto acumulado."""
        if dto.amount <= Decimal("0"):
            return Err(ValidationError("El monto del aporte debe ser mayor a cero."))

        goal_res = self.goal_repo.get_by_id(dto.savings_goal_id)
        if goal_res.is_err() or not goal_res.ok():
            return Err(ValidationError("La meta de ahorro especificada no existe."))

        goal = goal_res.ok()
        assert goal is not None

        if dto.currency != goal.currency:
            return Err(
                ValidationError(
                    f"La moneda del aporte ({dto.currency}) no coincide "
                    f"con la moneda de la meta ({goal.currency})."
                )
            )

        contrib = GoalContribution(
            savings_goal_id=dto.savings_goal_id,
            family_member_id=dto.family_member_id,
            amount=dto.amount,
            currency=dto.currency,
            source_type=dto.source_type,
            note=dto.note,
            fecha=dto.fecha,
        )

        contrib_res = self.contrib_repo.add(contrib)
        if contrib_res.is_err():
            return contrib_res

        # Actualizar acumulado de la meta
        new_amount = goal.current_amount + dto.amount
        is_completed = new_amount >= goal.target_amount
        self.goal_repo.update_current_amount(
            assert_goal_id(goal.id), new_amount, is_completed
        )

        return contrib_res

    def list_contributions(self, goal_id: int) -> list[GoalContribution]:
        """Lista el historial de aportes de una meta."""
        return self.contrib_repo.list_by_goal_id(goal_id)

    def simulate_goal(
        self,
        goal_id: int,
        monthly_savings: Decimal,
        labor_boost_amount: Decimal = Decimal("0.00"),
        labor_boost_desc: str = "",
    ) -> GoalSimulationResult:
        """
        Simula la cantidad de meses necesarios para alcanzar la meta.
        Compara ahorro regular contra escenario con inyección laboral.
        """
        goal_res = self.goal_repo.get_by_id(goal_id)
        if goal_res.is_err() or not goal_res.ok():
            return GoalSimulationResult(
                goal_id=goal_id,
                goal_name="",
                remaining_amount=Decimal("0"),
                currency="UYU",
                monthly_savings_amount=monthly_savings,
            )

        goal = goal_res.ok()
        assert goal is not None
        remaining = goal.remaining_amount

        if remaining <= Decimal("0"):
            today = date.today()
            return GoalSimulationResult(
                goal_id=goal_id,
                goal_name=goal.name,
                remaining_amount=Decimal("0"),
                currency=goal.currency,
                monthly_savings_amount=monthly_savings,
                months_regular_only=0,
                estimated_date_regular_only=today,
                months_with_labor_boost=0,
                estimated_date_with_labor_boost=today,
                labor_boost_description="¡Meta ya alcanzada!",
            )

        # 1. Escenario Solo Ahorro Mensual
        months_reg: int | None = None
        date_reg: date | None = None
        if monthly_savings > Decimal("0"):
            months_reg = math.ceil(float(remaining / monthly_savings))
            date_reg = _add_months(date.today(), months_reg)

        # 2. Escenario Con Inyección Laboral / Extra
        months_boost: int | None = None
        date_boost: date | None = None
        if labor_boost_amount > Decimal("0") or monthly_savings > Decimal("0"):
            # Simular mes a mes inyectando aguinaldos en junio y diciembre
            acum = Decimal("0")
            current_date = date.today()
            m_count = 0
            while acum < remaining and m_count < 120:  # tope de 10 años
                m_count += 1
                current_date = _add_months(date.today(), m_count)
                acum += monthly_savings
                # Si cae en Junio o Diciembre, inyectar el aporte laboral
                if labor_boost_amount > Decimal("0") and current_date.month in (6, 12):
                    acum += labor_boost_amount

            months_boost = m_count
            date_boost = current_date

        return GoalSimulationResult(
            goal_id=goal_id,
            goal_name=goal.name,
            remaining_amount=remaining,
            currency=goal.currency,
            monthly_savings_amount=monthly_savings,
            months_regular_only=months_reg,
            estimated_date_regular_only=date_reg,
            months_with_labor_boost=months_boost,
            estimated_date_with_labor_boost=date_boost,
            labor_boost_description=labor_boost_desc,
        )


def assert_goal_id(gid: int | None) -> int:
    if gid is None:
        raise ValueError("Goal ID cannot be None")
    return gid


def _add_months(orig_date: date, months: int) -> date:
    """Suma 'months' meses a una fecha."""
    month = orig_date.month - 1 + months
    year = orig_date.year + month // 12
    month = month % 12 + 1
    day = min(orig_date.day, 28)  # seguro para fin de mes
    return date(year, month, day)
