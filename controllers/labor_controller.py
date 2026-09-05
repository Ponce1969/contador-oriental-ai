"""
Controller para la gestión de actividades económicas, simulaciones y
cálculos laborales familiares.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

from result import Err, Ok, Result

from controllers.base_controller import BaseController
from core.unit_of_work import UnitOfWork
from models.errors import AppError, ValidationError
from repositories.economic_activity_repository import EconomicActivityRepository
from repositories.income_repository import IncomeRepository
from services.domain.labor_service import LaborService
from services.labor.domain.dtos import (
    FamilyIRPFOptimizerInput,
    FamilyIRPFOptimizerResult,
    IndependentProfile,
    PensionProfile,
)
from services.labor.domain.enums import ActivityNature
from services.labor.domain.fiscal_calendar_dtos import (
    FiscalCalendarRequest,
    FiscalCalendarSummary,
)
from services.labor.domain.models import (
    CalculationResult,
    EconomicActivity,
    TaxProfile,
)
from services.labor.engine import LaborCalculationEngine

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def parse_decimal(
    val: str | None, default: Decimal = Decimal("0.00")
) -> Result[Decimal, AppError]:
    """
    Convierte de forma segura y determinística un valor str proveniente de UI a Decimal.
    Cumple estrictamente con la política de CERO float y CERO round().
    """
    if val is None:
        return Ok(default)
    trimmed = val.strip()
    if not trimmed:
        return Ok(default)
    cleaned = trimmed.replace("$", "").replace(" ", "")
    if not cleaned:
        return Err(ValidationError(f"Formato numérico no válido: '{val}'"))

    # Manejo seguro de separadores decimales/miles
    if "," in cleaned and "." not in cleaned:
        cleaned = cleaned.replace(",", ".")
    elif "," in cleaned and "." in cleaned:
        if cleaned.find(".") < cleaned.find(","):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")

    # Rechazar notación científica o caracteres no monetarios
    if "e" in cleaned.lower():
        return Err(ValidationError(f"Formato numérico no válido: '{val}'"))

    try:
        dec = Decimal(cleaned)
        if dec.is_nan() or dec.is_infinite():
            return Err(ValidationError(f"Valor numérico no válido: '{val}'"))
        return Ok(dec)
    except (InvalidOperation, TypeError, ValueError):
        return Err(ValidationError(f"Formato numérico no válido: '{val}'"))


class LaborController(BaseController):
    """Controller para actividades económicas, simulaciones y beneficios laborales."""

    parse_decimal = staticmethod(parse_decimal)

    def __init__(
        self,
        session: Session | None = None,
        familia_id: int | None = None,
        uow: UnitOfWork | None = None,
    ) -> None:
        super().__init__(session=session, familia_id=familia_id, uow=uow)

    def get_title(self) -> str:
        return "Actividades y Beneficios Laborales"

    # =========================================================================
    # SIMULACIONES PURAS (Read-Only / Pure Compute - Cero persistencia)
    # =========================================================================

    def simulate_dependent(
        self,
        nominal_str: str,
        tax_profile: TaxProfile | None = None,
        fiscal_year: int = 2026,
    ) -> Result[CalculationResult, AppError]:
        """
        Simula retenciones mensuales para un dependiente a partir de un str de UI.
        No persiste datos en la base de datos.
        """
        parsed = parse_decimal(nominal_str)
        if parsed.is_err():
            return Err(parsed.unwrap_err())
        nominal = parsed.unwrap()
        profile = tax_profile or TaxProfile()
        result = LaborCalculationEngine.calculate_withholdings(
            nominal=nominal,
            profile=profile,
            fiscal_year=fiscal_year,
        )
        return Ok(result)

    def simulate_personal_services(
        self,
        billed_str: str,
        profile: IndependentProfile,
        fiscal_year: int = 2026,
        is_client_cede: bool = False,
        vat_rate_type: str = "BASIC",
        actual_expenses_str: str | None = None,
        withholdings_suffered_str: str = "0.00",
    ) -> Result[CalculationResult, AppError]:
        """
        Simula la liquidación bimestral de Servicios Personales.
        No persiste datos en la base de datos.
        """
        parsed_billed = parse_decimal(billed_str)
        if parsed_billed.is_err():
            return Err(parsed_billed.unwrap_err())

        parsed_withholdings = parse_decimal(withholdings_suffered_str)
        if parsed_withholdings.is_err():
            return Err(parsed_withholdings.unwrap_err())

        actual_expenses: Decimal | None = None
        if actual_expenses_str is not None:
            parsed_exp = parse_decimal(actual_expenses_str)
            if parsed_exp.is_err():
                return Err(parsed_exp.unwrap_err())
            actual_expenses = parsed_exp.unwrap()

        result = LaborCalculationEngine.calculate_personal_services(
            net_billed_amount=parsed_billed.unwrap(),
            profile=profile,
            fiscal_year=fiscal_year,
            is_client_cede=is_client_cede,
            vat_rate_type=vat_rate_type,
            actual_documented_expenses=actual_expenses,
            irpf_withholdings_suffered=parsed_withholdings.unwrap(),
        )
        return Ok(result)

    def simulate_literal_e(
        self,
        annual_sales_str: str,
        profile: IndependentProfile,
        fiscal_year: int = 2026,
        calculation_date: date | None = None,
    ) -> Result[CalculationResult, AppError]:
        """
        Simula la liquidación y elegibilidad de Pequeña Empresa (Literal E).
        No persiste datos en la base de datos.
        """
        parsed = parse_decimal(annual_sales_str)
        if parsed.is_err():
            return Err(parsed.unwrap_err())

        result = LaborCalculationEngine.calculate_literal_e(
            annual_gross_sales_uyu=parsed.unwrap(),
            profile=profile,
            fiscal_year=fiscal_year,
            calculation_date=calculation_date,
        )
        return Ok(result)

    def simulate_monotributo(
        self,
        annual_sales_str: str,
        profile: IndependentProfile,
        fiscal_year: int = 2026,
        calculation_date: date | None = None,
    ) -> Result[CalculationResult, AppError]:
        """
        Simula la liquidación y elegibilidad de Monotributo Común / Social MIDES.
        No persiste datos en la base de datos.
        """
        parsed = parse_decimal(annual_sales_str)
        if parsed.is_err():
            return Err(parsed.unwrap_err())

        result = LaborCalculationEngine.calculate_monotributo(
            annual_gross_sales_uyu=parsed.unwrap(),
            profile=profile,
            fiscal_year=fiscal_year,
            calculation_date=calculation_date,
        )
        return Ok(result)

    def simulate_pension(
        self,
        profile: PensionProfile,
        fiscal_year: int = 2026,
    ) -> Result[CalculationResult, AppError]:
        """
        Simula la liquidación de pasividades e IASS.
        No persiste datos en la base de datos.
        """
        result = LaborCalculationEngine.calculate_pension(
            profile=profile,
            fiscal_year=fiscal_year,
        )
        return Ok(result)

    # =========================================================================
    # PERSISTENCIA EXPLÍCITA (CRUD de Actividades Económicas)
    # =========================================================================

    def add_activity(
        self, activity: EconomicActivity
    ) -> Result[EconomicActivity, AppError]:
        """Agregar una nueva actividad económica."""
        with self._get_session() as session:
            activity_repo = EconomicActivityRepository(session, self._familia_id)
            income_repo = IncomeRepository(session, self._familia_id)
            service = LaborService(activity_repo, income_repo)
            res = service.create_activity(activity)
            if res.is_ok() and activity.nature == ActivityNature.INDEPENDIENTE:
                try:
                    from database.tables import FamilyMemberTable

                    mem = (
                        session.query(FamilyMemberTable)
                        .filter(FamilyMemberTable.id == activity.family_member_id)
                        .first()
                    )
                    if mem and mem.estado_laboral != "independiente":
                        mem.estado_laboral = "independiente"
                        session.commit()
                except Exception:
                    pass
            return res

    def get_activity(self, activity_id: int) -> Result[EconomicActivity, AppError]:
        """Obtener una actividad económica por ID."""
        with self._get_session() as session:
            activity_repo = EconomicActivityRepository(session, self._familia_id)
            income_repo = IncomeRepository(session, self._familia_id)
            service = LaborService(activity_repo, income_repo)
            return service.get_activity(activity_id)

    def list_by_member(self, member_id: int) -> list[EconomicActivity]:
        """Listar actividades de un integrante."""
        with self._get_session() as session:
            activity_repo = EconomicActivityRepository(session, self._familia_id)
            income_repo = IncomeRepository(session, self._familia_id)
            service = LaborService(activity_repo, income_repo)
            return service.list_activities_by_member(member_id)

    def list_all_activities(self) -> list[EconomicActivity]:
        """Listar todas las actividades de la familia."""
        with self._get_session() as session:
            activity_repo = EconomicActivityRepository(session, self._familia_id)
            income_repo = IncomeRepository(session, self._familia_id)
            service = LaborService(activity_repo, income_repo)
            return service.list_all_activities()

    def update_activity(
        self, activity: EconomicActivity
    ) -> Result[EconomicActivity, AppError]:
        """Actualizar una actividad económica."""
        with self._get_session() as session:
            activity_repo = EconomicActivityRepository(session, self._familia_id)
            income_repo = IncomeRepository(session, self._familia_id)
            service = LaborService(activity_repo, income_repo)
            res = service.update_activity(activity)
            if res.is_ok() and activity.nature == ActivityNature.INDEPENDIENTE:
                try:
                    from database.tables import FamilyMemberTable

                    mem = (
                        session.query(FamilyMemberTable)
                        .filter(FamilyMemberTable.id == activity.family_member_id)
                        .first()
                    )
                    if mem and mem.estado_laboral != "independiente":
                        mem.estado_laboral = "independiente"
                        session.commit()
                except Exception:
                    pass
            return res

    def delete_activity(self, activity_id: int) -> Result[None, AppError]:
        """Eliminar una actividad económica."""
        with self._get_session() as session:
            activity_repo = EconomicActivityRepository(session, self._familia_id)
            income_repo = IncomeRepository(session, self._familia_id)
            service = LaborService(activity_repo, income_repo)
            return service.delete_activity(activity_id)

    def calculate_aguinaldo(
        self,
        activity_id: int,
        year: int,
        semester: int,
        today: date | None = None,
    ) -> Result[CalculationResult, AppError]:
        """Calcular aguinaldo para una actividad económica."""
        with self._get_session() as session:
            activity_repo = EconomicActivityRepository(session, self._familia_id)
            income_repo = IncomeRepository(session, self._familia_id)
            service = LaborService(activity_repo, income_repo)
            return service.calculate_member_aguinaldo(
                activity_id, year, semester, today=today
            )

    def calculate_vacation_pay(
        self,
        activity_id: int,
        requested_days: int = 20,
    ) -> Result[CalculationResult, AppError]:
        """Calcular salario vacacional orientativo para una actividad económica."""
        with self._get_session() as session:
            activity_repo = EconomicActivityRepository(session, self._familia_id)
            income_repo = IncomeRepository(session, self._familia_id)
            service = LaborService(activity_repo, income_repo)
            return service.calculate_member_vacation_pay(
                activity_id, requested_days=requested_days
            )

    def optimizar_irpf_familiar(
        self,
        input_data: FamilyIRPFOptimizerInput,
    ) -> Result[FamilyIRPFOptimizerResult, AppError]:
        """
        Calcula y compara la liquidación de IRPF Individual vs. Núcleo Familiar (DGI).
        Aplica deducciones conjuntas y crédito fiscal del 8% (Ley 18.083 / 18.719).
        """
        try:
            res = LaborCalculationEngine.optimize_family_irpf(input_data)
            if res is None:
                return Err(
                    ValidationError(
                        f"Sin reglas fiscales para el año {input_data.year}."
                    )
                )
            return Ok(res)
        except Exception as ex:
            return Err(ValidationError(f"Error en simulación de IRPF familiar: {ex}"))

    def obtener_calendario_fiscal(
        self,
        year: int,
        month: int,
        last_digit: int | None = None,
        reference_date: date | None = None,
    ) -> Result[FiscalCalendarSummary, AppError]:
        """
        Calcula el calendario fiscal determinístico del mes para la familia.
        """
        try:
            activities = self.list_all_activities()
            req = FiscalCalendarRequest(
                year=year,
                month=month,
                rut_last_digit=last_digit,
                reference_date=reference_date,
            )
            summary = LaborCalculationEngine.calculate_fiscal_calendar(
                request=req,
                activities=activities,
            )
            return Ok(summary)
        except Exception as ex:
            return Err(ValidationError(f"Error generando calendario fiscal: {ex}"))
