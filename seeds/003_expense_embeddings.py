"""
Seed: poblar expenses.embedding con embeddings semánticos para los gastos
del seed anterior (notas='seed_test'). Permite búsqueda cosine via pgvector.

Idempotente: solo procesa gastos con embedding IS NULL.
"""

from __future__ import annotations

import asyncio
import logging
import os

from database.engine import get_session
from database.tables import ExpenseTable
from repositories.expense_repository import ExpenseRepository
from services.ai.embedding_service import EmbeddingService

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def _get_familia_id(session) -> int:
    from sqlalchemy import text

    row = session.execute(
        text("SELECT familia_id FROM usuarios WHERE username = 'admin' LIMIT 1")
    ).fetchone()
    if not row:
        raise RuntimeError("Usuario 'admin' no encontrado.")
    return row[0]


def _formatear_gasto(g: ExpenseTable) -> str:
    return (
        f"Gasto registrado: {g.descripcion} "
        f"por ${g.monto:,.0f} "
        f"en categoría {g.categoria}. "
        f"Método: {g.metodo_pago}. "
        f"Fecha: {g.fecha}."
    )


async def _poblar(session) -> tuple[int, int]:
    familia_id = _get_familia_id(session)
    embedding_service = EmbeddingService()
    repo = ExpenseRepository(session, familia_id)

    gastos = (
        session.query(ExpenseTable)
        .filter(
            ExpenseTable.familia_id == familia_id,
            ExpenseTable.notas == "seed_test",
            ExpenseTable.embedding.is_(None),
        )
        .order_by(ExpenseTable.fecha)
        .all()
    )

    if not gastos:
        print("  ✓  Todos los gastos ya tienen embedding.")
        return 0, familia_id

    print(
        f"  📦 Generando embeddings para {len(gastos)} gastos en expenses.embedding..."
    )
    ok_count = 0

    for g in gastos:
        texto = _formatear_gasto(g)
        result = await embedding_service.generar_embedding(texto)
        if hasattr(result, "ok") and result.ok():
            repo.guardar_embedding(g.id, result.ok())
            ok_count += 1
            print(
                f"  ✅ [{ok_count:02d}/{len(gastos)}] {g.fecha} | {g.descripcion[:45]}"
            )
        else:
            print(f"  ❌ Error embedding: {g.descripcion} — {result}")

    return ok_count, familia_id


def run(db):
    if os.getenv("APP_ENV") == "production":
        print("  ⛔ Seeds deshabilitados en APP_ENV=production. Abortando.")
        return
    session = get_session()
    try:
        total, familia_id = asyncio.run(_poblar(session))
        print(
            f"\n  🔍 {total} embeddings guardados en expenses.embedding para familia_id={familia_id}"
        )
    except Exception as e:
        session.rollback()
        print(f"  ❌ Error en seed de embeddings: {e}")
        raise
    finally:
        session.close()
