"""
Repository para la gestión de actividades económicas de los miembros familiares.
"""

from __future__ import annotations

from decimal import Decimal

from result import Err, Ok, Result
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database.tables import (
    DependentDetailsTable,
    EconomicActivityTable,
    IndependentDetailsTable,
)
from models.errors import DatabaseError
from services.labor.domain.dtos import IndependentProfile
from services.labor.domain.enums import (
    ActivityNature,
    IndependentTaxRegime,
    PensionFundType,
    RemunerationType,
)
from services.labor.domain.models import DependentDetails, EconomicActivity


def _activity_to_domain(
    row: EconomicActivityTable,
    details_row: DependentDetailsTable | None = None,
    ind_row: IndependentDetailsTable | None = None,
) -> EconomicActivity:
    details = None
    if details_row:
        details = DependentDetails(
            id=details_row.id,
            economic_activity_id=details_row.economic_activity_id,
            remuneration_type=RemunerationType(details_row.remuneration_type),
            weekly_hours=details_row.weekly_hours,
            estimated_monthly_nominal=details_row.estimated_monthly_nominal,
        )

    independent_profile = None
    if ind_row:
        regime_val = (
            IndependentTaxRegime(ind_row.regime)
            if ind_row.regime in [r.value for r in IndependentTaxRegime]
            else IndependentTaxRegime.MONOTRIBUTO
        )
        pension_val = (
            PensionFundType(ind_row.pension_fund)
            if ind_row.pension_fund in [p.value for p in PensionFundType]
            else PensionFundType.BPS
        )
        independent_profile = IndependentProfile(
            id=ind_row.id,
            economic_activity_id=ind_row.economic_activity_id,
            regime=regime_val,
            pension_fund=pension_val,
            estimated_monthly_gross_sales=ind_row.estimated_monthly_gross_sales,
            partner_count=ind_row.partner_count,
            employees_count=ind_row.employees_count,
            has_mides_certificate=ind_row.has_mides_certificate,
        )
    elif row.nature == ActivityNature.INDEPENDIENTE.value:
        # Fallback synthesis from title if details table row doesn't exist yet
        title_lower = (row.title or "").lower()
        if "monotributo" in title_lower:
            regime_val = IndependentTaxRegime.MONOTRIBUTO
            fund_val = PensionFundType.BPS
            sales_val = Decimal("150000.00")
        elif "literal" in title_lower:
            regime_val = IndependentTaxRegime.LITERAL_E
            fund_val = PensionFundType.BPS
            sales_val = Decimal("0.00")
        else:
            regime_val = IndependentTaxRegime.SERVICIOS_PERSONALES
            fund_val = PensionFundType.CJPPU
            sales_val = Decimal("0.00")

        independent_profile = IndependentProfile(
            regime=regime_val,
            pension_fund=fund_val,
            estimated_monthly_gross_sales=sales_val,
        )

    return EconomicActivity(
        id=row.id,
        familia_id=row.familia_id,
        family_member_id=row.family_member_id,
        nature=ActivityNature(row.nature),
        title=row.title,
        start_date=row.start_date,
        end_date=row.end_date,
        is_active=row.is_active,
        dependent_details=details,
        independent_profile=independent_profile,
    )


class EconomicActivityRepository:
    """Repository para operaciones CRUD de actividades económicas y vínculos."""

    def __init__(self, session: Session, familia_id: int | None = None) -> None:
        self.session = session
        self.familia_id = familia_id

    def add(
        self, activity: EconomicActivity
    ) -> Result[EconomicActivity, DatabaseError]:
        """Crear una nueva actividad económica."""
        try:
            row = EconomicActivityTable(
                familia_id=activity.familia_id,
                family_member_id=activity.family_member_id,
                nature=activity.nature.value,
                title=activity.title,
                start_date=activity.start_date,
                end_date=activity.end_date,
                is_active=activity.is_active,
            )
            self.session.add(row)
            self.session.flush()

            saved_details = None
            if activity.dependent_details:
                details_row = DependentDetailsTable(
                    economic_activity_id=row.id,
                    remuneration_type=activity.dependent_details.remuneration_type.value,
                    weekly_hours=activity.dependent_details.weekly_hours,
                    estimated_monthly_nominal=activity.dependent_details.estimated_monthly_nominal,
                )
                self.session.add(details_row)
                self.session.flush()
                saved_details = details_row

            saved_ind_details = None
            if activity.independent_profile:
                reg_str = (
                    activity.independent_profile.regime.value
                    if hasattr(activity.independent_profile.regime, "value")
                    else str(activity.independent_profile.regime)
                )
                fund_str = (
                    activity.independent_profile.pension_fund.value
                    if hasattr(activity.independent_profile.pension_fund, "value")
                    else str(activity.independent_profile.pension_fund or "bps")
                )
                ind_row = IndependentDetailsTable(
                    economic_activity_id=row.id,
                    regime=reg_str,
                    pension_fund=fund_str,
                    estimated_monthly_gross_sales=activity.independent_profile.estimated_monthly_gross_sales,
                    partner_count=activity.independent_profile.partner_count or 1,
                    employees_count=activity.independent_profile.employees_count or 0,
                    has_mides_certificate=activity.independent_profile.has_mides_certificate
                    or False,
                )
                self.session.add(ind_row)
                self.session.flush()
                saved_ind_details = ind_row

            return Ok(_activity_to_domain(row, saved_details, saved_ind_details))
        except SQLAlchemyError as e:
            return Err(
                DatabaseError(message=f"Error al guardar actividad económica: {e}")
            )

    def get_by_id(self, activity_id: int) -> Result[EconomicActivity, DatabaseError]:
        """Obtener una actividad económica por ID."""
        try:
            query = self.session.query(EconomicActivityTable).filter(
                EconomicActivityTable.id == activity_id
            )
            if self.familia_id is not None:
                query = query.filter(
                    EconomicActivityTable.familia_id == self.familia_id
                )
            row = query.first()
            if not row:
                return Err(
                    DatabaseError(
                        message=f"Actividad económica {activity_id} no encontrada."
                    )
                )

            details_row = (
                self.session.query(DependentDetailsTable)
                .filter(DependentDetailsTable.economic_activity_id == row.id)
                .first()
            )
            ind_row = (
                self.session.query(IndependentDetailsTable)
                .filter(IndependentDetailsTable.economic_activity_id == row.id)
                .first()
            )

            return Ok(_activity_to_domain(row, details_row, ind_row))
        except SQLAlchemyError as e:
            return Err(
                DatabaseError(message=f"Error al obtener actividad económica: {e}")
            )

    def list_by_member(self, member_id: int) -> list[EconomicActivity]:
        """Listar todas las actividades económicas de un integrante."""
        query = self.session.query(EconomicActivityTable).filter(
            EconomicActivityTable.family_member_id == member_id
        )
        if self.familia_id is not None:
            query = query.filter(EconomicActivityTable.familia_id == self.familia_id)

        rows = query.order_by(
            EconomicActivityTable.is_active.desc(), EconomicActivityTable.id.desc()
        ).all()
        results: list[EconomicActivity] = []
        for row in rows:
            details_row = (
                self.session.query(DependentDetailsTable)
                .filter(DependentDetailsTable.economic_activity_id == row.id)
                .first()
            )
            ind_row = (
                self.session.query(IndependentDetailsTable)
                .filter(IndependentDetailsTable.economic_activity_id == row.id)
                .first()
            )
            results.append(_activity_to_domain(row, details_row, ind_row))
        return results

    def list_all_by_family(self) -> list[EconomicActivity]:
        """Listar todas las actividades económicas de la familia."""
        if self.familia_id is None:
            return []
        query = self.session.query(EconomicActivityTable).filter(
            EconomicActivityTable.familia_id == self.familia_id
        )
        rows = query.order_by(
            EconomicActivityTable.is_active.desc(), EconomicActivityTable.id.desc()
        ).all()
        results: list[EconomicActivity] = []
        for row in rows:
            details_row = (
                self.session.query(DependentDetailsTable)
                .filter(DependentDetailsTable.economic_activity_id == row.id)
                .first()
            )
            ind_row = (
                self.session.query(IndependentDetailsTable)
                .filter(IndependentDetailsTable.economic_activity_id == row.id)
                .first()
            )
            results.append(_activity_to_domain(row, details_row, ind_row))
        return results

    def update(
        self, activity: EconomicActivity
    ) -> Result[EconomicActivity, DatabaseError]:
        """Actualizar una actividad económica existente."""
        try:
            if activity.id is None:
                return Err(
                    DatabaseError(
                        message="ID requerido para actualizar actividad económica."
                    )
                )

            query = self.session.query(EconomicActivityTable).filter(
                EconomicActivityTable.id == activity.id
            )
            if self.familia_id is not None:
                query = query.filter(
                    EconomicActivityTable.familia_id == self.familia_id
                )
            row = query.first()
            if not row:
                return Err(
                    DatabaseError(
                        message=f"Actividad económica {activity.id} no encontrada."
                    )
                )

            row.nature = activity.nature.value
            row.title = activity.title
            row.start_date = activity.start_date
            row.end_date = activity.end_date
            row.is_active = activity.is_active

            # Actualizar o insertar DependentDetails
            details_row = (
                self.session.query(DependentDetailsTable)
                .filter(DependentDetailsTable.economic_activity_id == row.id)
                .first()
            )

            if activity.dependent_details:
                if details_row:
                    details_row.remuneration_type = (
                        activity.dependent_details.remuneration_type.value
                    )
                    details_row.weekly_hours = activity.dependent_details.weekly_hours
                    details_row.estimated_monthly_nominal = (
                        activity.dependent_details.estimated_monthly_nominal
                    )
                else:
                    details_row = DependentDetailsTable(
                        economic_activity_id=row.id,
                        remuneration_type=activity.dependent_details.remuneration_type.value,
                        weekly_hours=activity.dependent_details.weekly_hours,
                        estimated_monthly_nominal=activity.dependent_details.estimated_monthly_nominal,
                    )
                    self.session.add(details_row)
            elif details_row:
                self.session.delete(details_row)
                details_row = None

            # Actualizar o insertar IndependentDetails
            ind_row = (
                self.session.query(IndependentDetailsTable)
                .filter(IndependentDetailsTable.economic_activity_id == row.id)
                .first()
            )

            if activity.independent_profile:
                reg_str = (
                    activity.independent_profile.regime.value
                    if hasattr(activity.independent_profile.regime, "value")
                    else str(activity.independent_profile.regime)
                )
                fund_str = (
                    activity.independent_profile.pension_fund.value
                    if hasattr(activity.independent_profile.pension_fund, "value")
                    else str(activity.independent_profile.pension_fund or "bps")
                )
                if ind_row:
                    ind_row.regime = reg_str
                    ind_row.pension_fund = fund_str
                    ind_row.estimated_monthly_gross_sales = (
                        activity.independent_profile.estimated_monthly_gross_sales
                    )
                    ind_row.partner_count = (
                        activity.independent_profile.partner_count or 1
                    )
                    ind_row.employees_count = (
                        activity.independent_profile.employees_count or 0
                    )
                    ind_row.has_mides_certificate = (
                        activity.independent_profile.has_mides_certificate or False
                    )
                else:
                    ind_row = IndependentDetailsTable(
                        economic_activity_id=row.id,
                        regime=reg_str,
                        pension_fund=fund_str,
                        estimated_monthly_gross_sales=activity.independent_profile.estimated_monthly_gross_sales,
                        partner_count=activity.independent_profile.partner_count or 1,
                        employees_count=activity.independent_profile.employees_count
                        or 0,
                        has_mides_certificate=activity.independent_profile.has_mides_certificate
                        or False,
                    )
                    self.session.add(ind_row)
            elif ind_row:
                self.session.delete(ind_row)
                ind_row = None

            self.session.flush()
            return Ok(_activity_to_domain(row, details_row, ind_row))
        except SQLAlchemyError as e:
            return Err(
                DatabaseError(message=f"Error al actualizar actividad económica: {e}")
            )

    def delete(self, activity_id: int) -> Result[None, DatabaseError]:
        """Eliminar una actividad económica."""
        try:
            query = self.session.query(EconomicActivityTable).filter(
                EconomicActivityTable.id == activity_id
            )
            if self.familia_id is not None:
                query = query.filter(
                    EconomicActivityTable.familia_id == self.familia_id
                )
            row = query.first()
            if not row:
                return Err(
                    DatabaseError(
                        message=f"Actividad económica {activity_id} no encontrada."
                    )
                )

            self.session.delete(row)
            self.session.flush()
            return Ok(None)
        except SQLAlchemyError as e:
            return Err(
                DatabaseError(message=f"Error al eliminar actividad económica: {e}")
            )
