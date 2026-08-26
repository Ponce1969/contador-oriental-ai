"""
Modelos de dominio para Metas de Ahorro Familiar (Savings Goals).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class GoalCategory(StrEnum):
    """Categorías de metas de ahorro familiar."""

    GENERAL = "general"
    VEHICLE = "vehicle"
    TRAVEL = "travel"
    EMERGENCY = "emergency"
    HOME = "home"
    EDUCATION = "education"


class ContributionSource(StrEnum):
    """Fuente de financiamiento del aporte."""

    REGULAR_INCOME = "regular_income"  # Ahorro mensual regular
    AGUINALDO_JUNE = "aguinaldo_june"  # Aguinaldo Junio (Ley 12.840)
    AGUINALDO_DECEMBER = "aguinaldo_december"  # Aguinaldo Diciembre (Ley 12.840)
    VACATION_PAY = "vacation_pay"  # Salario Vacacional (Ley 16.101)
    EXTRA_INVOICE = "extra_invoice"  # Cobro extra / Trabajo unipersonal / Monotributo
    MANUAL_DEPOSIT = "manual_deposit"  # Aporte manual general


class GoalContribution(BaseModel):
    """Registro de aporte o depósito hacia una meta de ahorro."""

    id: int | None = None
    savings_goal_id: int
    family_member_id: int | None = None
    amount: Decimal = Field(gt=Decimal("0"), description="Monto del aporte")
    currency: str = Field(default="UYU", description="Moneda: UYU o USD")
    source_type: ContributionSource = Field(default=ContributionSource.REGULAR_INCOME)
    note: str | None = None
    fecha: date = Field(default_factory=date.today)
    created_at: datetime = Field(default_factory=datetime.now)

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, value: str) -> str:
        v = value.strip().upper()
        if v not in ("UYU", "USD"):
            raise ValueError("currency debe ser 'UYU' o 'USD'")
        return v


class GoalContributionCreate(BaseModel):
    """DTO para crear un nuevo aporte."""

    savings_goal_id: int
    family_member_id: int | None = None
    amount: Decimal = Field(gt=Decimal("0"))
    currency: str = "UYU"
    source_type: ContributionSource = ContributionSource.REGULAR_INCOME
    note: str | None = None
    fecha: date = Field(default_factory=date.today)

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, value: str) -> str:
        v = value.strip().upper()
        if v not in ("UYU", "USD"):
            raise ValueError("currency debe ser 'UYU' o 'USD'")
        return v


class SavingsGoal(BaseModel):
    """Meta de Ahorro Familiar (Alcancía del Hogar)."""

    id: int | None = None
    familia_id: int
    name: str = Field(min_length=1, max_length=120)
    target_amount: Decimal = Field(gt=Decimal("0"), description="Monto objetivo")
    currency: str = Field(default="UYU", description="Moneda: UYU o USD")
    current_amount: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0"), description="Monto ahorrado"
    )
    deadline: date | None = None
    category: GoalCategory = Field(default=GoalCategory.GENERAL)
    icon: str = Field(default="savings")
    color: str = Field(default="#6200EE")
    is_completed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @property
    def progress_pct(self) -> float:
        """Porcentaje alcanzado respecto al objetivo (0.0 a 100.0%)."""
        if self.target_amount <= Decimal("0"):
            return 0.0
        pct = float((self.current_amount / self.target_amount) * 100)
        return min(pct, 100.0)

    @property
    def remaining_amount(self) -> Decimal:
        """Monto faltante para alcanzar la meta."""
        rem = self.target_amount - self.current_amount
        return max(rem, Decimal("0.00"))

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, value: str) -> str:
        v = value.strip().upper()
        if v not in ("UYU", "USD"):
            raise ValueError("currency debe ser 'UYU' o 'USD'")
        return v


class SavingsGoalCreate(BaseModel):
    """DTO para crear una nueva meta."""

    familia_id: int
    name: str = Field(min_length=1, max_length=120)
    target_amount: Decimal = Field(gt=Decimal("0"))
    currency: str = "UYU"
    deadline: date | None = None
    category: GoalCategory = GoalCategory.GENERAL
    icon: str = "savings"
    color: str = "#6200EE"

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, value: str) -> str:
        v = value.strip().upper()
        if v not in ("UYU", "USD"):
            raise ValueError("currency debe ser 'UYU' o 'USD'")
        return v


class SavingsGoalUpdate(BaseModel):
    """DTO para actualizar una meta existente."""

    name: str | None = None
    target_amount: Decimal | None = None
    currency: str | None = None
    deadline: date | None = None
    category: GoalCategory | None = None
    icon: str | None = None
    color: str | None = None
    is_completed: bool | None = None


class GoalSimulationResult(BaseModel):
    """Resultado de la proyección temporal para alcanzar una meta."""

    goal_id: int
    goal_name: str
    remaining_amount: Decimal
    currency: str
    monthly_savings_amount: Decimal
    months_regular_only: int | None = None
    estimated_date_regular_only: date | None = None
    months_with_labor_boost: int | None = None
    estimated_date_with_labor_boost: date | None = None
    labor_boost_description: str = ""
