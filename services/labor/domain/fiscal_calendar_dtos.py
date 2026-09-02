"""
Modelos de dominio, DTOs y enumeraciones para el Calendario Fiscal Oficial.
Garantiza separación estricta entre estado de fecha y estado de importe,
con tipado 100% Decimal y datetime.date.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class FiscalEntity(StrEnum):
    """Organismos recaudadores oficiales de Uruguay."""

    DGI = "DGI"
    BPS = "BPS"
    CJPPU = "CJPPU"


class FiscalObligationType(StrEnum):
    """Tipos de obligaciones tributarias y previsionales reglamentadas."""

    IRPF_ANTICIPO_BIMESTRAL = "IRPF_ANTICIPO_BIMESTRAL"
    LITERAL_E_CUOTA_MENSUAL = "LITERAL_E_CUOTA_MENSUAL"
    MONOTRIBUTO_DGI = "MONOTRIBUTO_DGI"
    IVA_SERVICIOS_PERSONALES = "IVA_SERVICIOS_PERSONALES"
    IRPF_IASS_DECLARACION_ANUAL = "IRPF_IASS_DECLARACION_ANUAL"
    BPS_SERVICIO_DOMESTICO = "BPS_SERVICIO_DOMESTICO"
    BPS_NO_DEPENDIENTES = "BPS_NO_DEPENDIENTES"
    MONOTRIBUTO_BPS = "MONOTRIBUTO_BPS"
    CJPPU_APORTE_MENSUAL = "CJPPU_APORTE_MENSUAL"


class DateVerificationStatus(StrEnum):
    """Nivel de certeza y respaldo normativo de la fecha de vencimiento."""

    OFFICIAL_VERIFIED = "OFFICIAL_VERIFIED"
    REGULATORY_RULE = "REGULATORY_RULE"
    FALLBACK = "FALLBACK"


class AmountStatus(StrEnum):
    """Nivel de certeza del importe monetario asociado."""

    EXACT_LEGAL = "EXACT_LEGAL"
    CALCULATED_ESTIMATE = "CALCULATED_ESTIMATE"
    USER_DECLARED = "USER_DECLARED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class OfficialDateAuditEntry(BaseModel):
    """
    Entrada puntual del calendario oficial publicado con respaldo de auditoría.
    """

    organism: FiscalEntity
    fiscal_year: int
    obligation_type: FiscalObligationType
    month: int = Field(ge=1, le=12)
    taxpayer_group: str
    due_date: date
    source_document: str
    source_reference: str
    source_url: str
    verification_status: DateVerificationStatus = (
        DateVerificationStatus.OFFICIAL_VERIFIED
    )
    notes: str | None = None


class FiscalDueDateInfo(BaseModel):
    """
    Representación inmutable de una obligación fiscal con separación
    estricta de estado de fecha, estado de importe y trazabilidad.
    """

    obligation_id: str
    entity: FiscalEntity
    obligation_type: FiscalObligationType
    title: str
    target_period_label: str

    # ── Estado y Fecha ────────────────────────────────────────────────
    due_date: date
    date_status: DateVerificationStatus

    # ── Estado e Importe ──────────────────────────────────────────────
    estimated_amount: Decimal | None = None
    amount_status: AmountStatus
    currency: Literal["UYU", "USD"] = "UYU"

    # ── Trazabilidad, Alertas y Auditoría ──────────────────────────────
    days_remaining: int
    urgency_level: Literal["VENCIDO", "HOY", "URGENTE", "PROXIMO", "FUTURO"]
    legal_source: str
    source_reference: str
    source_url: str
    notes: str | None = None


class FiscalCalendarRequest(BaseModel):
    """Parámetros de consulta al motor de calendario fiscal."""

    year: int = Field(ge=2024, le=2030)
    month: int = Field(ge=1, le=12)
    rut_last_digit: int | None = Field(default=None, ge=0, le=9)
    entities: list[FiscalEntity] | None = None
    obligation_types: list[FiscalObligationType] | None = None
    reference_date: date | None = None


class FiscalCalendarSummary(BaseModel):
    """Resumen consolidado del calendario fiscal para un período."""

    year: int
    month: int
    rut_last_digit: int | None
    reference_date: date
    obligations: list[FiscalDueDateInfo]
    total_estimated_amount_uyu: Decimal
    total_estimated_amount_usd: Decimal
    official_ruleset_version: str
