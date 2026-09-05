"""
Motor determinístico para resolución de vencimientos y calendario fiscal uruguayo.
Resuelve fechas con trazabilidad oficial, aplica reglas de corrimiento respaldadas
y calcula montos estimados en Decimal absoluto acoplados al motor laboral.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from services.labor.domain.dtos import IndependentProfile
from services.labor.domain.enums import (
    ActivityNature,
    IndependentTaxRegime,
    PensionFundType,
)
from services.labor.domain.fiscal_calendar_dtos import (
    AmountStatus,
    FiscalCalendarRequest,
    FiscalCalendarSummary,
    FiscalDueDateInfo,
    FiscalEntity,
    FiscalObligationType,
)
from services.labor.domain.fiscal_calendar_rules import (
    get_official_calendar_ruleset,
)
from services.labor.domain.models import EconomicActivity
from services.labor.engine import LaborCalculationEngine


def _map_digit_to_group(digit: int) -> str:
    """Mapea un dígito (0-9) al grupo oficial de DGI/BPS."""
    if digit in (0, 1, 2):
        return "0-2"
    elif digit in (3, 4, 5):
        return "3-5"
    elif digit in (6, 7, 8):
        return "6-8"
    else:
        return "9"


def _calculate_urgency(
    days: int,
) -> Literal["VENCIDO", "HOY", "URGENTE", "PROXIMO", "FUTURO"]:
    """Calcula el nivel de urgencia en base a los días restantes."""
    if days < 0:
        return "VENCIDO"
    elif days == 0:
        return "HOY"
    elif days <= 3:
        return "URGENTE"
    elif days <= 7:
        return "PROXIMO"
    else:
        return "FUTURO"


class FiscalCalendarCalculator:
    """Calculador determinístico de vencimientos fiscales con trazabilidad oficial."""

    @staticmethod
    def calculate_calendar(
        request: FiscalCalendarRequest,
        activities: list[EconomicActivity] | None = None,
    ) -> FiscalCalendarSummary:
        """
        Calcula el resumen de vencimientos fiscales del mes respetando:
        1. Prioridad absoluta de fechas oficiales publicadas
        2. Separación estricta de estado de fecha vs estado de importe
        3. Identificación de obligaciones según actividades registradas
        """
        ref_date = request.reference_date or date.today()
        ruleset = get_official_calendar_ruleset(request.year)

        if not ruleset:
            return FiscalCalendarSummary(
                year=request.year,
                month=request.month,
                rut_last_digit=request.rut_last_digit,
                reference_date=ref_date,
                obligations=[],
                total_estimated_amount_uyu=Decimal("0.00"),
                total_estimated_amount_usd=Decimal("0.00"),
                official_ruleset_version="FALLBACK-NO-RULESET",
            )

        last_digit = request.rut_last_digit if request.rut_last_digit is not None else 0
        digit_group = _map_digit_to_group(last_digit)

        applicable_obligations: set[FiscalObligationType] = set()
        activity_by_obligation: dict[FiscalObligationType, EconomicActivity] = {}

        if activities:
            for act in activities:
                if not act.is_active:
                    continue
                is_indep = act.nature == ActivityNature.INDEPENDIENTE
                if is_indep:
                    regime = (
                        act.independent_profile.regime
                        if act.independent_profile
                        else None
                    )
                    if not regime:
                        title_lower = (act.title or "").lower()
                        if "monotributo" in title_lower:
                            regime = IndependentTaxRegime.MONOTRIBUTO
                        elif "literal" in title_lower:
                            regime = IndependentTaxRegime.LITERAL_E
                        elif "servicio" in title_lower:
                            regime = IndependentTaxRegime.SERVICIOS_PERSONALES

                    if regime == IndependentTaxRegime.LITERAL_E:
                        applicable_obligations.add(
                            FiscalObligationType.LITERAL_E_CUOTA_MENSUAL
                        )
                        activity_by_obligation[
                            FiscalObligationType.LITERAL_E_CUOTA_MENSUAL
                        ] = act
                    elif regime in (
                        IndependentTaxRegime.MONOTRIBUTO,
                        IndependentTaxRegime.MONOTRIBUTO_MIDES,
                    ):
                        applicable_obligations.add(FiscalObligationType.MONOTRIBUTO_DGI)
                        applicable_obligations.add(FiscalObligationType.MONOTRIBUTO_BPS)
                        activity_by_obligation[FiscalObligationType.MONOTRIBUTO_DGI] = (
                            act
                        )
                        activity_by_obligation[FiscalObligationType.MONOTRIBUTO_BPS] = (
                            act
                        )
                    elif regime == IndependentTaxRegime.SERVICIOS_PERSONALES:
                        applicable_obligations.add(
                            FiscalObligationType.IRPF_ANTICIPO_BIMESTRAL
                        )
                        applicable_obligations.add(
                            FiscalObligationType.IVA_SERVICIOS_PERSONALES
                        )
                        activity_by_obligation[
                            FiscalObligationType.IRPF_ANTICIPO_BIMESTRAL
                        ] = act
        else:
            applicable_obligations = {
                FiscalObligationType.LITERAL_E_CUOTA_MENSUAL,
                FiscalObligationType.IRPF_ANTICIPO_BIMESTRAL,
                FiscalObligationType.BPS_SERVICIO_DOMESTICO,
                FiscalObligationType.CJPPU_APORTE_MENSUAL,
            }

        if request.obligation_types:
            applicable_obligations = applicable_obligations.intersection(
                set(request.obligation_types)
            )

        due_date_infos: list[FiscalDueDateInfo] = []
        total_uyu = Decimal("0.00")
        total_usd = Decimal("0.00")

        for entry in ruleset.entries:
            if entry.month != request.month:
                continue
            if entry.obligation_type not in applicable_obligations:
                continue
            if request.entities and entry.organism not in request.entities:
                continue

            if entry.taxpayer_group not in (digit_group, "ALL", "PROFESIONALES"):
                continue

            days_rem = (entry.due_date - ref_date).days
            urgency = _calculate_urgency(days_rem)

            est_amount, amt_status = (
                FiscalCalendarCalculator._estimate_obligation_amount(
                    entry.obligation_type,
                    request.year,
                    activity_by_obligation.get(entry.obligation_type),
                )
            )

            title = FiscalCalendarCalculator._format_title(
                entry.obligation_type, entry.organism
            )
            target_period = FiscalCalendarCalculator._format_period_label(
                entry.obligation_type, request.year, request.month
            )

            ob_id = (
                f"{entry.organism.value}_{entry.obligation_type.value}_"
                f"{request.year}_{request.month:02d}"
            )
            info = FiscalDueDateInfo(
                obligation_id=ob_id,
                entity=entry.organism,
                obligation_type=entry.obligation_type,
                title=title,
                target_period_label=target_period,
                due_date=entry.due_date,
                date_status=entry.verification_status,
                estimated_amount=est_amount,
                amount_status=amt_status,
                currency="UYU",
                days_remaining=days_rem,
                urgency_level=urgency,
                legal_source=entry.source_document,
                source_reference=entry.source_reference,
                source_url=entry.source_url,
                notes=entry.notes,
            )
            due_date_infos.append(info)

            if est_amount and amt_status != AmountStatus.NOT_APPLICABLE:
                total_uyu += est_amount

        due_date_infos.sort(key=lambda x: x.due_date)

        return FiscalCalendarSummary(
            year=request.year,
            month=request.month,
            rut_last_digit=request.rut_last_digit,
            reference_date=ref_date,
            obligations=due_date_infos,
            total_estimated_amount_uyu=total_uyu.quantize(Decimal("0.01")),
            total_estimated_amount_usd=total_usd.quantize(Decimal("0.01")),
            official_ruleset_version=ruleset.ruleset_version,
        )

    @staticmethod
    def _estimate_obligation_amount(
        ob_type: FiscalObligationType,
        year: int,
        activity: EconomicActivity | None,
    ) -> tuple[Decimal | None, AmountStatus]:
        """Calcula el importe oficial o estimado según la actividad registrada."""
        if not activity:
            return None, AmountStatus.NOT_APPLICABLE

        prof = activity.independent_profile
        if not prof:
            title_lower = (activity.title or "").lower()
            if "monotributo" in title_lower:
                prof = IndependentProfile(
                    regime=IndependentTaxRegime.MONOTRIBUTO,
                    pension_fund=PensionFundType.BPS,
                    estimated_monthly_gross_sales=Decimal("150000.00"),
                )
            elif "literal" in title_lower:
                prof = IndependentProfile(
                    regime=IndependentTaxRegime.LITERAL_E,
                    pension_fund=PensionFundType.BPS,
                    estimated_monthly_gross_sales=Decimal("0.00"),
                )
            elif "servicio" in title_lower:
                prof = IndependentProfile(
                    regime=IndependentTaxRegime.SERVICIOS_PERSONALES,
                    pension_fund=PensionFundType.CJPPU,
                    estimated_monthly_gross_sales=Decimal("0.00"),
                )
            else:
                return None, AmountStatus.NOT_APPLICABLE
        try:
            if ob_type == FiscalObligationType.LITERAL_E_CUOTA_MENSUAL:
                sales = (
                    prof.estimated_monthly_gross_sales or Decimal("0.00")
                ) * Decimal("12")
                res = LaborCalculationEngine.calculate_literal_e(
                    annual_gross_sales_uyu=sales,
                    profile=prof,
                    fiscal_year=year,
                )
                if (
                    res.literal_e_payload
                    and res.literal_e_payload.dgi_monthly_fee > Decimal("0.00")
                ):
                    return (
                        res.literal_e_payload.dgi_monthly_fee,
                        AmountStatus.EXACT_LEGAL,
                    )

            mono_types = (
                FiscalObligationType.MONOTRIBUTO_DGI,
                FiscalObligationType.MONOTRIBUTO_BPS,
            )
            if ob_type in mono_types:
                sales = (
                    prof.estimated_monthly_gross_sales or Decimal("0.00")
                ) * Decimal("12")
                res = LaborCalculationEngine.calculate_monotributo(
                    annual_gross_sales_uyu=sales,
                    profile=prof,
                    fiscal_year=year,
                )
                if (
                    res.monotributo_payload
                    and res.monotributo_payload.final_monthly_monotributo_fee
                    > Decimal("0.00")
                ):
                    return (
                        res.monotributo_payload.final_monthly_monotributo_fee,
                        AmountStatus.EXACT_LEGAL,
                    )

            if ob_type == FiscalObligationType.IRPF_ANTICIPO_BIMESTRAL:
                m_sales = prof.estimated_monthly_gross_sales or Decimal("0.00")
                if m_sales > Decimal("0.00"):
                    res = LaborCalculationEngine.calculate_personal_services(
                        net_billed_amount=m_sales * Decimal("2"),
                        profile=prof,
                        fiscal_year=year,
                    )
                    if (
                        res.personal_services_payload
                        and res.personal_services_payload.irpf_advance_amount
                        > Decimal("0.00")
                    ):
                        return (
                            res.personal_services_payload.irpf_advance_amount,
                            AmountStatus.CALCULATED_ESTIMATE,
                        )
        except Exception:
            pass

        return None, AmountStatus.NOT_APPLICABLE

    @staticmethod
    def _format_title(ob_type: FiscalObligationType, entity: FiscalEntity) -> str:
        """Retorna un título claro y legible para el usuario."""
        titles = {
            FiscalObligationType.LITERAL_E_CUOTA_MENSUAL: (
                "DGI - Cuota Mensual Literal E (Pequeña Empresa)"
            ),
            FiscalObligationType.MONOTRIBUTO_DGI: (
                "DGI / BPS - Cuota Única Monotributo"
            ),
            FiscalObligationType.MONOTRIBUTO_BPS: (
                "BPS - Aporte Monotributo Unificado"
            ),
            FiscalObligationType.IRPF_ANTICIPO_BIMESTRAL: (
                "DGI - Anticipo Bimestral IRPF (Servicios Personales)"
            ),
            FiscalObligationType.IVA_SERVICIOS_PERSONALES: (
                "DGI - Anticipo Bimestral IVA (Servicios Personales)"
            ),
            FiscalObligationType.BPS_SERVICIO_DOMESTICO: (
                "BPS - Aportes Servicio Doméstico (ATYR)"
            ),
            FiscalObligationType.BPS_NO_DEPENDIENTES: (
                "BPS - Aportes Trabajadores No Dependientes"
            ),
            FiscalObligationType.CJPPU_APORTE_MENSUAL: (
                "CJPPU - Aporte Mensual Caja Profesional"
            ),
            FiscalObligationType.IRPF_IASS_DECLARACION_ANUAL: (
                "DGI - Declaración Jurada Anual IRPF / IASS"
            ),
        }
        return titles.get(ob_type, f"{entity.value} - {ob_type.value}")

    @staticmethod
    def _format_period_label(
        ob_type: FiscalObligationType, year: int, month: int
    ) -> str:
        """Formatea el período que se está liquidando o pagando."""
        month_names = [
            "",
            "Enero",
            "Febrero",
            "Marzo",
            "Abril",
            "Mayo",
            "Junio",
            "Julio",
            "Agosto",
            "Setiembre",
            "Octubre",
            "Noviembre",
            "Diciembre",
        ]
        bimonth_obs = (
            FiscalObligationType.IRPF_ANTICIPO_BIMESTRAL,
            FiscalObligationType.IVA_SERVICIOS_PERSONALES,
        )
        if ob_type in bimonth_obs:
            bimester_num = month // 2
            b_start = bimester_num * 2 - 1
            b_end = bimester_num * 2
            if 1 <= b_start <= 12 and 1 <= b_end <= 12:
                return f"Bimestre {month_names[b_start]} - {month_names[b_end]} {year}"

        prev_m = month - 1 if month > 1 else 12
        prev_y = year if month > 1 else year - 1
        return f"Cargo {month_names[prev_m]} {prev_y}"
