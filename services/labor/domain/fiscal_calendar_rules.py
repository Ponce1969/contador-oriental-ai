"""
RuleSets oficiales y datasets versionados para el Calendario Fiscal Uruguayo.
Cada vencimiento oficial conserva respaldo de auditoría:
organism, fiscal_year, obligation_type, taxpayer_group, due_date, source_document,
source_reference, source_url y verification_status.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from services.labor.domain.fiscal_calendar_dtos import (
    DateVerificationStatus,
    FiscalEntity,
    FiscalObligationType,
    OfficialDateAuditEntry,
)


class FiscalCalendarRuleSet(BaseModel):
    """Conjunto normativo oficial de calendario fiscal para un ejercicio."""

    fiscal_year: int
    ruleset_version: str
    entries: list[OfficialDateAuditEntry]
    legal_framework: str


def _build_official_calendar_2026() -> FiscalCalendarRuleSet:
    """
    Construye el calendario oficial 2026 con respaldo de resoluciones oficiales:
    - DGI: Resolución DGI Nº 2520/2025 (Cuadro General de Vencimientos 2026)
    - BPS: Comunicado BPS Cobranza ATYR / No Dependientes 2026
    - CJPPU: Calendario Oficial de Pagos CJPPU Ejercicio 2026
    """
    entries: list[OfficialDateAuditEntry] = []

    dgi_doc = "Resolución DGI Nº 2520/2025"
    dgi_url = (
        "https://www.dgi.gub.uy/wdgi/page?2,principal,"
        "dgi--calendario-de-vencimientos,O,es,0,"
    )
    dgi_note = (
        "Pago mensual a mes vencido en redes de cobranza (Abitab/RedPagos/DGI en línea)"
    )

    dgi_rut_matrix_2026: dict[int, dict[str, int]] = {
        1: {"0-2": 22, "3-5": 23, "6-8": 26, "9": 27},
        2: {"0-2": 23, "3-5": 24, "6-8": 25, "9": 26},
        3: {"0-2": 23, "3-5": 24, "6-8": 25, "9": 26},
        4: {"0-2": 22, "3-5": 23, "6-8": 24, "9": 27},
        5: {"0-2": 22, "3-5": 25, "6-8": 26, "9": 27},
        6: {"0-2": 22, "3-5": 23, "6-8": 24, "9": 25},
        7: {"0-2": 22, "3-5": 23, "6-8": 24, "9": 27},
        8: {"0-2": 24, "3-5": 26, "6-8": 27, "9": 28},
        9: {"0-2": 22, "3-5": 23, "6-8": 24, "9": 25},
        10: {"0-2": 22, "3-5": 23, "6-8": 26, "9": 27},
        11: {"0-2": 23, "3-5": 24, "6-8": 25, "9": 26},
        12: {"0-2": 22, "3-5": 23, "6-8": 24, "9": 28},
    }

    for m, groups in dgi_rut_matrix_2026.items():
        for grp, d in groups.items():
            ref_str = f"Cuadro Vencimientos DGI 2026 - Numeral 3 (Mes {m}, Grupo {grp})"
            mono_ref = (
                f"Cuadro Vencimientos DGI 2026 - Monotributo (Mes {m}, Grupo {grp})"
            )
            entries.append(
                OfficialDateAuditEntry(
                    organism=FiscalEntity.DGI,
                    fiscal_year=2026,
                    obligation_type=FiscalObligationType.LITERAL_E_CUOTA_MENSUAL,
                    month=m,
                    taxpayer_group=grp,
                    due_date=date(2026, m, d),
                    source_document=dgi_doc,
                    source_reference=ref_str,
                    source_url=dgi_url,
                    verification_status=DateVerificationStatus.OFFICIAL_VERIFIED,
                    notes=dgi_note,
                )
            )
            entries.append(
                OfficialDateAuditEntry(
                    organism=FiscalEntity.DGI,
                    fiscal_year=2026,
                    obligation_type=FiscalObligationType.MONOTRIBUTO_DGI,
                    month=m,
                    taxpayer_group=grp,
                    due_date=date(2026, m, d),
                    source_document=dgi_doc,
                    source_reference=mono_ref,
                    source_url=dgi_url,
                    verification_status=DateVerificationStatus.OFFICIAL_VERIFIED,
                    notes="Cuota única mensual DGI/BPS",
                )
            )

    irpf_bimonthly_2026: dict[int, tuple[int, str]] = {
        3: (25, "Bimestre 1 (Enero - Febrero 2026)"),
        5: (25, "Bimestre 2 (Marzo - Abril 2026)"),
        7: (27, "Bimestre 3 (Mayo - Junio 2026)"),
        9: (25, "Bimestre 4 (Julio - Agosto 2026)"),
        11: (25, "Bimestre 5 (Setiembre - Octubre 2026)"),
    }

    for m, (d, period_desc) in irpf_bimonthly_2026.items():
        ref_bimonth = f"Cuadro Vencimientos DGI 2026 - Numeral 5 ({period_desc})"
        entries.append(
            OfficialDateAuditEntry(
                organism=FiscalEntity.DGI,
                fiscal_year=2026,
                obligation_type=FiscalObligationType.IRPF_ANTICIPO_BIMESTRAL,
                month=m,
                taxpayer_group="ALL",
                due_date=date(2026, m, d),
                source_document=dgi_doc,
                source_reference=ref_bimonth,
                source_url=dgi_url,
                verification_status=DateVerificationStatus.OFFICIAL_VERIFIED,
                notes=f"Anticipo bimestral de IRPF Categoría II. {period_desc}",
            )
        )
        entries.append(
            OfficialDateAuditEntry(
                organism=FiscalEntity.DGI,
                fiscal_year=2026,
                obligation_type=FiscalObligationType.IVA_SERVICIOS_PERSONALES,
                month=m,
                taxpayer_group="ALL",
                due_date=date(2026, m, d),
                source_document=dgi_doc,
                source_reference=ref_bimonth,
                source_url=dgi_url,
                verification_status=DateVerificationStatus.OFFICIAL_VERIFIED,
                notes=f"Anticipo bimestral IVA Servicios Personales. {period_desc}",
            )
        )

    bps_doc = "Comunicado BPS Calendario de Pagos ATYR 2026"
    bps_url = "https://www.bps.gub.uy/11025/calendario-de-pagos.html"

    bps_domestico_matrix_2026: dict[int, int] = {
        1: 28,
        2: 27,
        3: 27,
        4: 28,
        5: 28,
        6: 26,
        7: 28,
        8: 28,
        9: 28,
        10: 28,
        11: 27,
        12: 28,
    }

    for m, d in bps_domestico_matrix_2026.items():
        bps_dom_ref = f"BPS Calendario Cobranza 2026 - Doméstico Mes {m}"
        bps_no_dep_ref = f"BPS Calendario Cobranza 2026 - No Dependientes Mes {m}"
        entries.append(
            OfficialDateAuditEntry(
                organism=FiscalEntity.BPS,
                fiscal_year=2026,
                obligation_type=FiscalObligationType.BPS_SERVICIO_DOMESTICO,
                month=m,
                taxpayer_group="ALL",
                due_date=date(2026, m, d),
                source_document=bps_doc,
                source_reference=bps_dom_ref,
                source_url=bps_url,
                verification_status=DateVerificationStatus.OFFICIAL_VERIFIED,
                notes=(
                    "Aportes a la seguridad social de servicio doméstico (Ley 18.065)"
                ),
            )
        )
        entries.append(
            OfficialDateAuditEntry(
                organism=FiscalEntity.BPS,
                fiscal_year=2026,
                obligation_type=FiscalObligationType.BPS_NO_DEPENDIENTES,
                month=m,
                taxpayer_group="ALL",
                due_date=date(2026, m, d),
                source_document=bps_doc,
                source_reference=bps_no_dep_ref,
                source_url=bps_url,
                verification_status=DateVerificationStatus.OFFICIAL_VERIFIED,
                notes="Aportes patronales/personales BPS trabajadores independientes",
            )
        )

    cjppu_doc = "Calendario Oficial de Pagos CJPPU 2026"
    cjppu_url = "https://www.cjppu.org.uy/calendario_pagos.php"

    cjppu_matrix_2026: dict[int, int] = {
        1: 26,
        2: 25,
        3: 25,
        4: 27,
        5: 26,
        6: 25,
        7: 27,
        8: 25,
        9: 25,
        10: 26,
        11: 25,
        12: 28,
    }

    for m, d in cjppu_matrix_2026.items():
        cjppu_note = (
            "Aporte mensual por categoría profesional universitaria "
            "(Ley 17.738 / Ley 20.212)"
        )
        entries.append(
            OfficialDateAuditEntry(
                organism=FiscalEntity.CJPPU,
                fiscal_year=2026,
                obligation_type=FiscalObligationType.CJPPU_APORTE_MENSUAL,
                month=m,
                taxpayer_group="PROFESIONALES",
                due_date=date(2026, m, d),
                source_document=cjppu_doc,
                source_reference=f"CJPPU Calendario 2026 - Aportes Mes {m}",
                source_url=cjppu_url,
                verification_status=DateVerificationStatus.OFFICIAL_VERIFIED,
                notes=cjppu_note,
            )
        )

    framework = (
        "Res. DGI 2520/2025; Comunicado BPS ATYR 2026; "
        "Res. CJPPU 2026; Código Tributario Art. 8"
    )
    return FiscalCalendarRuleSet(
        fiscal_year=2026,
        ruleset_version="UY-FISCAL-CALENDAR-2026.1",
        entries=entries,
        legal_framework=framework,
    )


_OFFICIAL_CALENDARS: dict[int, FiscalCalendarRuleSet] = {
    2026: _build_official_calendar_2026(),
}


def get_official_calendar_ruleset(year: int) -> FiscalCalendarRuleSet | None:
    """Obtiene el RuleSet oficial verificado para el año fiscal."""
    return _OFFICIAL_CALENDARS.get(year)
