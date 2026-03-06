"""Modelos Pydantic y SQLAlchemy."""

from __future__ import annotations

from datetime import date, datetime  # noqa: TCH003

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class OCRSession(Base):
    __tablename__ = "ocr_sessions"

    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    familia_id: Mapped[int] = mapped_column(Integer, nullable=False)
    resultado_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


def get_engine(database_url: str):
    return create_engine(database_url, pool_pre_ping=True)


def init_db(database_url: str) -> None:
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)


def get_session(database_url: str) -> Session:
    engine = get_engine(database_url)
    return Session(engine)


class OCRResponse(BaseModel):
    """Respuesta OCR."""

    success: bool
    monto: float | None = None
    comercio: str | None = None
    fecha: date | None = None
    items: list[str] = Field(default_factory=list)
    categoria_sugerida: str | None = None
    confianza_ocr: float = Field(default=0.0, ge=0.0, le=1.0)
    texto_crudo: str = ""
    error: str | None = None


class HealthResponse(BaseModel):
    """Health check."""

    status: str
    version: str
