"""
Tests para el sistema de Metas de Ahorro Familiar (Savings Goals).
"""

from __future__ import annotations

from decimal import Decimal

import pydantic
import pytest

from models.ai_model import AIContext
from models.savings_goal_model import (
    ContributionSource,
    GoalCategory,
    GoalContributionCreate,
    SavingsGoalCreate,
    SavingsGoalUpdate,
)
from services.ai.ai_advisor_service import AIAdvisorService
from services.savings_goal_service import SavingsGoalService


class TestSavingsGoalService:
    """Tests unitarios para SavingsGoalService y simulación de metas."""

    @pytest.fixture
    def service(self, db_session):
        return SavingsGoalService(db_session, familia_id=1)

    @pytest.fixture
    def other_service(self, db_session):
        return SavingsGoalService(db_session, familia_id=2)

    def test_crear_meta_valida(self, service):
        dto = SavingsGoalCreate(
            familia_id=1,
            name="Vacaciones en Rocha",
            target_amount=Decimal("40000.00"),
            currency="UYU",
            category=GoalCategory.TRAVEL,
        )
        res = service.create_goal(dto)
        assert res.is_ok()
        goal = res.ok()
        assert goal is not None
        assert goal.id is not None
        assert goal.name == "Vacaciones en Rocha"
        assert goal.target_amount == Decimal("40000.00")
        assert goal.current_amount == Decimal("0.00")
        assert goal.progress_pct == 0.0
        assert goal.remaining_amount == Decimal("40000.00")
        assert goal.is_completed is False

    def test_crear_meta_monto_invalido(self, service):
        with pytest.raises(pydantic.ValidationError):
            SavingsGoalCreate(
                familia_id=1,
                name="Auto",
                target_amount=Decimal("0.00"),
            )

    def test_crear_meta_nombre_vacio(self, service):
        with pytest.raises(pydantic.ValidationError):
            SavingsGoalCreate(
                familia_id=1,
                name="",
                target_amount=Decimal("10000.00"),
            )

    def test_actualizar_meta(self, service):
        dto = SavingsGoalCreate(
            familia_id=1,
            name="Pintar la Casa",
            target_amount=Decimal("20000.00"),
            currency="UYU",
            category=GoalCategory.HOME,
        )
        create_res = service.create_goal(dto)
        assert create_res.is_ok()
        goal = create_res.ok()
        assert goal is not None
        assert goal.id is not None

        update_dto = SavingsGoalUpdate(
            name="Pintar y Reparar Techo",
            target_amount=Decimal("35000.00"),
        )
        update_res = service.update_goal(goal.id, update_dto)
        assert update_res.is_ok()
        updated = update_res.ok()
        assert updated is not None
        assert updated.name == "Pintar y Reparar Techo"
        assert updated.target_amount == Decimal("35000.00")

    def test_aislamiento_multitenant(self, service, other_service):
        dto1 = SavingsGoalCreate(
            familia_id=1,
            name="Meta Familia 1",
            target_amount=Decimal("15000.00"),
        )
        dto2 = SavingsGoalCreate(
            familia_id=2,
            name="Meta Familia 2",
            target_amount=Decimal("50000.00"),
        )
        service.create_goal(dto1)
        other_service.create_goal(dto2)

        goals1 = service.list_goals()
        goals2 = other_service.list_goals()

        assert len(goals1) == 1
        assert goals1[0].name == "Meta Familia 1"
        assert len(goals2) == 1
        assert goals2[0].name == "Meta Familia 2"

    def test_registrar_aporte_y_completar_meta(self, service):
        dto = SavingsGoalCreate(
            familia_id=1,
            name="Fondo Emergencia",
            target_amount=Decimal("10000.00"),
            currency="UYU",
            category=GoalCategory.EMERGENCY,
        )
        goal = service.create_goal(dto).ok()
        assert goal is not None
        assert goal.id is not None

        # 1er aporte parcial
        contrib1 = GoalContributionCreate(
            savings_goal_id=goal.id,
            amount=Decimal("4000.00"),
            currency="UYU",
            source_type=ContributionSource.REGULAR_INCOME,
            note="Ahorro enero",
        )
        res1 = service.add_contribution(contrib1)
        assert res1.is_ok()

        g_after1 = service.get_goal(goal.id).ok()
        assert g_after1 is not None
        assert g_after1.current_amount == Decimal("4000.00")
        assert g_after1.progress_pct == 40.0
        assert g_after1.remaining_amount == Decimal("6000.00")
        assert g_after1.is_completed is False

        # 2do aporte que completa la meta
        contrib2 = GoalContributionCreate(
            savings_goal_id=goal.id,
            amount=Decimal("6000.00"),
            currency="UYU",
            source_type=ContributionSource.AGUINALDO_JUNE,
            note="Fracción de aguinaldo",
        )
        res2 = service.add_contribution(contrib2)
        assert res2.is_ok()

        g_after2 = service.get_goal(goal.id).ok()
        assert g_after2 is not None
        assert g_after2.current_amount == Decimal("10000.00")
        assert g_after2.progress_pct == 100.0
        assert g_after2.remaining_amount == Decimal("0.00")
        assert g_after2.is_completed is True

        # Historial de aportes
        contribs = service.list_contributions(goal.id)
        assert len(contribs) == 2

    def test_registrar_aporte_moneda_incompatible_falla(self, service):
        dto = SavingsGoalCreate(
            familia_id=1,
            name="Viaje Exterior",
            target_amount=Decimal("1500.00"),
            currency="USD",
        )
        goal = service.create_goal(dto).ok()
        assert goal is not None
        assert goal.id is not None

        # Intentar aportar en UYU a una meta en USD
        contrib = GoalContributionCreate(
            savings_goal_id=goal.id,
            amount=Decimal("5000.00"),
            currency="UYU",
        )
        res = service.add_contribution(contrib)
        assert res.is_err()
        assert "no coincide con la moneda de la meta" in str(res.err())

    def test_simulacion_proyeccion_temporal(self, service):
        dto = SavingsGoalCreate(
            familia_id=1,
            name="Cambio de Coche",
            target_amount=Decimal("120000.00"),
            currency="UYU",
        )
        goal = service.create_goal(dto).ok()
        assert goal is not None
        assert goal.id is not None

        # Simulación con $10.000 mensual solo vs $10.000 mensual + $20.000 de aguinaldo
        sim = service.simulate_goal(
            goal_id=goal.id,
            monthly_savings=Decimal("10000.00"),
            labor_boost_amount=Decimal("20000.00"),
            labor_boost_desc="50% del aguinaldo proyectado",
        )

        assert sim.goal_id == goal.id
        assert sim.remaining_amount == Decimal("120000.00")
        assert sim.months_regular_only == 12  # 120.000 / 10.000 = 12 meses
        assert sim.months_with_labor_boost is not None
        assert sim.months_with_labor_boost < 12  # Con aguinaldos se reduce
        assert "50% del aguinaldo" in sim.labor_boost_description

    def test_ai_advisor_formateo_metas(self):
        advisor = AIAdvisorService()
        ctx = AIContext(
            resumen_metas=(
                "=== METAS DE AHORRO ACTIVAS DEL HOGAR ===\n"
                "- Meta: 'Vacaciones' | Objetivo: $ 50 000 | "
                "Acumulado: $ 25 000 (50.0%) | Faltante: $ 25 000"
            )
        )

        # Pregunta sobre metas: debe incluir la sección
        texto_metas = advisor._formatear_datos_metas(
            ctx, pregunta="¿Cómo venimos con las metas de ahorro?"
        )
        assert "METAS DE AHORRO Y ALCANCÍAS DEL HOGAR" in texto_metas
        assert "Vacaciones" in texto_metas

        # Pregunta no relacionada: no debe inyectarla para optimizar tokens
        texto_irrel = advisor._formatear_datos_metas(
            ctx, pregunta="¿Cuánto gasté en el supermercado?"
        )
        assert texto_irrel == ""
