"""
Modelo SQLAlchemy para la tabla ai_vector_memory (memoria vectorial RAG)
"""
from __future__ import annotations

from sqlalchemy import Integer, String, TIMESTAMP, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class MemoriaVectorial(Base):
    """Tabla de memoria vectorial para el Contador Oriental (pgvector)"""
    __tablename__ = "ai_vector_memory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    familia_id: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list | None] = mapped_column(nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[str | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"MemoriaVectorial(id={self.id}, "
            f"familia_id={self.familia_id}, "
            f"source_type={self.source_type!r})"
        )
