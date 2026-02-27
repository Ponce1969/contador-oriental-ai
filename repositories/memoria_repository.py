"""
MemoriaRepository — Acceso a la tabla ai_vector_memory con búsqueda semántica.
Usa SQL directo para las operaciones vectoriales (pgvector <=> cosine distance).
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class MemoriaRepository:
    """
    Repository para ai_vector_memory.
    Usa SQL directo con pgvector para máximo control sobre el índice HNSW.
    """

    def __init__(self, session: Session, familia_id: int) -> None:
        self.session = session
        self.familia_id = familia_id

    def guardar(
        self,
        content: str,
        embedding: list[float],
        source_type: str | None = None,
        source_id: int | None = None,
    ) -> int | None:
        """
        Guardar un registro en la memoria vectorial.

        Returns:
            ID del registro creado, o None si falla.
        """
        try:
            result = self.session.execute(
                text("""
                    INSERT INTO ai_vector_memory
                        (familia_id, content, embedding, source_type, source_id)
                    VALUES
                        (:fam_id, :content, :emb, :src_type, :src_id)
                    RETURNING id
                """),
                {
                    "fam_id": self.familia_id,
                    "content": content,
                    "emb": str(embedding),
                    "src_type": source_type,
                    "src_id": source_id,
                },
            )
            self.session.flush()
            row = result.fetchone()
            return row[0] if row else None
        except Exception as e:
            logger.error("[MEMORIA_REPO] Error al guardar: %s", str(e))
            return None

    def buscar_similares(
        self,
        embedding: list[float],
        limit: int = 5,
        source_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Buscar registros semánticamente similares usando cosine distance HNSW.

        Args:
            embedding: Vector de consulta (768 dims de nomic-embed-text).
            limit: Máximo de resultados.
            source_type: Filtrar por tipo ('expense', 'income', 'snapshot').

        Returns:
            Lista de dicts con {id, content, source_type, source_id, distance}.
        """
        try:
            if source_type:
                result = self.session.execute(
                    text("""
                        SELECT id, content, source_type, source_id,
                               embedding <=> :emb AS distance
                        FROM ai_vector_memory
                        WHERE familia_id = :fam_id
                          AND source_type = :src_type
                        ORDER BY embedding <=> :emb
                        LIMIT :lim
                    """),
                    {
                        "fam_id": self.familia_id,
                        "emb": str(embedding),
                        "src_type": source_type,
                        "lim": limit,
                    },
                )
            else:
                result = self.session.execute(
                    text("""
                        SELECT id, content, source_type, source_id,
                               embedding <=> :emb AS distance
                        FROM ai_vector_memory
                        WHERE familia_id = :fam_id
                        ORDER BY embedding <=> :emb
                        LIMIT :lim
                    """),
                    {
                        "fam_id": self.familia_id,
                        "emb": str(embedding),
                        "lim": limit,
                    },
                )

            rows = result.fetchall()
            return [
                {
                    "id": row[0],
                    "content": row[1],
                    "source_type": row[2],
                    "source_id": row[3],
                    "distance": float(row[4]) if row[4] is not None else 1.0,
                }
                for row in rows
            ]
        except Exception as e:
            logger.error("[MEMORIA_REPO] Error en búsqueda semántica: %s", str(e))
            return []

    def buscar_por_source(
        self, source_type: str, source_id: int
    ) -> dict[str, Any] | None:
        """Verificar si ya existe un recuerdo para este source_type + source_id."""
        try:
            result = self.session.execute(
                text("""
                    SELECT id, content, source_type, source_id
                    FROM ai_vector_memory
                    WHERE familia_id = :fam_id
                      AND source_type = :src_type
                      AND source_id = :src_id
                    LIMIT 1
                """),
                {
                    "fam_id": self.familia_id,
                    "src_type": source_type,
                    "src_id": source_id,
                },
            )
            row = result.fetchone()
            if row:
                return {
                    "id": row[0],
                    "content": row[1],
                    "source_type": row[2],
                    "source_id": row[3],
                }
            return None
        except Exception as e:
            logger.error("[MEMORIA_REPO] Error buscando por source: %s", str(e))
            return None

    def count(self) -> int:
        """Contar registros de esta familia en la memoria."""
        try:
            result = self.session.execute(
                text(
                    "SELECT COUNT(*) FROM ai_vector_memory "
                    "WHERE familia_id = :fam_id"
                ),
                {"fam_id": self.familia_id},
            )
            row = result.fetchone()
            return int(row[0]) if row else 0
        except Exception as e:
            logger.error("[MEMORIA_REPO] Error al contar: %s", str(e))
            return 0
