"""
Controller para la gestión de Metas de Ahorro Familiar (Savings Goals).
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from result import Err, Result

from controllers.base_controller import BaseController
from models.errors import AppError, DatabaseError
from models.savings_goal_model import (
    ContributionSource,
    GoalCategory,
    GoalContribution,
    GoalContributionCreate,
    GoalSimulationResult,
    SavingsGoal,
    SavingsGoalCreate,
    SavingsGoalUpdate,
)
from services.labor.engine import LaborCalculationEngine
from services.savings_goal_service import SavingsGoalService

logger = logging.getLogger(__name__)


class SavingsGoalController(BaseController):
    """Controller para operaciones de Metas de Ahorro."""

    def get_title(self) -> str:
        return "Metas de Ahorro"

    def crear_meta(
        self,
        name: str,
        target_amount: Decimal,
        currency: str = "UYU",
        deadline: date | None = None,
        category: GoalCategory = GoalCategory.GENERAL,
        icon: str = "savings",
        color: str = "#6200EE",
    ) -> Result[SavingsGoal, AppError]:
        """Crea una nueva meta de ahorro para la familia."""
        if not self._familia_id:
            return Err(DatabaseError("familia_id no configurado"))

        dto = SavingsGoalCreate(
            familia_id=self._familia_id,
            name=name,
            target_amount=target_amount,
            currency=currency,
            deadline=deadline,
            category=category,
            icon=icon,
            color=color,
        )

        with self._get_session() as session:
            service = SavingsGoalService(session, self._familia_id)
            res = service.create_goal(dto)
            if res.is_ok():
                session.commit()
            return res

    def actualizar_meta(
        self, goal_id: int, dto: SavingsGoalUpdate
    ) -> Result[SavingsGoal, AppError]:
        """Actualiza una meta de ahorro."""
        with self._get_session() as session:
            service = SavingsGoalService(session, self._familia_id)
            res = service.update_goal(goal_id, dto)
            if res.is_ok():
                session.commit()
            return res

    def eliminar_meta(self, goal_id: int) -> Result[bool, AppError]:
        """Elimina una meta de ahorro."""
        with self._get_session() as session:
            service = SavingsGoalService(session, self._familia_id)
            res = service.delete_goal(goal_id)
            if res.is_ok():
                session.commit()
            return res

    def obtener_metas(self, activas_solo: bool = False) -> list[SavingsGoal]:
        """Obtiene las metas de ahorro de la familia."""
        with self._get_session() as session:
            service = SavingsGoalService(session, self._familia_id)
            return service.list_goals(active_only=activas_solo)

    def registrar_aporte(
        self,
        goal_id: int,
        amount: Decimal,
        currency: str = "UYU",
        family_member_id: int | None = None,
        source_type: ContributionSource = ContributionSource.REGULAR_INCOME,
        note: str | None = None,
        contribution_date: date | None = None,
    ) -> Result[GoalContribution, AppError]:
        """Registra un aporte o depósito en la alcancía."""
        dto = GoalContributionCreate(
            savings_goal_id=goal_id,
            family_member_id=family_member_id,
            amount=amount,
            currency=currency,
            source_type=source_type,
            note=note,
            fecha=contribution_date or date.today(),
        )

        with self._get_session() as session:
            service = SavingsGoalService(session, self._familia_id)
            res = service.add_contribution(dto)
            if res.is_ok():
                session.commit()
            return res

    def obtener_aportes(self, goal_id: int) -> list[GoalContribution]:
        """Obtiene el historial de aportes de una meta."""
        with self._get_session() as session:
            service = SavingsGoalService(session, self._familia_id)
            return service.list_contributions(goal_id)

    def simular_meta_con_contexto_laboral(
        self,
        goal_id: int,
        monthly_savings: Decimal,
        aguinaldo_pct: Decimal = Decimal("50.0"),
    ) -> GoalSimulationResult:
        """
        Simula los tiempos para alcanzar la meta integrando beneficios laborales.
        Calcula el próximo aguinaldo estimado de integrantes dependientes/pasivos.
        """
        with self._get_session() as session:
            service = SavingsGoalService(session, self._familia_id)

            # Obtener miembros y calcular aguinaldos proyectados
            labor_boost = Decimal("0.00")
            boost_desc = ""
            try:
                from repositories.economic_activity_repository import (
                    EconomicActivityRepository,
                )
                from repositories.family_member_repository import (
                    FamilyMemberRepository,
                )
                from services.labor.domain.periods import CalculationPeriod

                member_repo = FamilyMemberRepository(session, self._familia_id)
                act_repo = EconomicActivityRepository(session, self._familia_id)
                members_res = member_repo.get_all()
                members = members_res.ok() if members_res.is_ok() else []

                today = date.today()
                period = CalculationPeriod(year=today.year, month=today.month)
                total_aguinaldos_hogar = Decimal("0.00")

                for m in members:
                    if not m or not m.id or not m.activo:
                        continue
                    activities = act_repo.get_by_family_member(m.id)
                    for act in activities:
                        if not act.is_active:
                            continue
                        if act.nature.value == "dependiente" and act.dependent_details:
                            sal = (
                                act.dependent_details.estimated_monthly_nominal
                                or Decimal("0")
                            )
                            if sal > 0:
                                res_ag = LaborCalculationEngine.calculate_aguinaldo(
                                    period, [(today.month, sal)]
                                )
                                if res_ag.status.value == "calculated":
                                    total_aguinaldos_hogar += res_ag.final_amount

                if total_aguinaldos_hogar > Decimal("0"):
                    factor = aguinaldo_pct / Decimal("100.0")
                    labor_boost = total_aguinaldos_hogar * factor
                    boost_desc = (
                        f"Inyección de {aguinaldo_pct:.0f}% del aguinaldo estimado "
                        f"($ {labor_boost:,.0f} UYU en Junio y Diciembre)"
                    ).replace(",", ".")
            except Exception as ex:
                logger.warning("Error calculando boost laboral para meta: %s", ex)

            return service.simulate_goal(
                goal_id=goal_id,
                monthly_savings=monthly_savings,
                labor_boost_amount=labor_boost,
                labor_boost_desc=boost_desc,
            )
