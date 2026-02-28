"""
Seed: poblar expenses.embedding con embeddings semánticos para los gastos
del seed anterior (notas='seed_test'). Permite búsqueda cosine via pgvector.

Idempotente: solo procesa gastos con embedding IS NULL.
"""

from __future__ import annotations

import asyncio
import logging

from database.engine import get_session
from database.tables import ExpenseTable
from repositories.expense_repository import ExpenseRepository
from services.embedding_service import EmbeddingService

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

FAMILIA_ID = 3


def _formatear_gasto(g: ExpenseTable) -> str:
    return (
        f"Gasto registrado: {g.descripcion} "
        f"por ${g.monto:,.0f} "
        f"en categoría {g.categoria}. "
        f"Método: {g.metodo_pago}. "
        f"Fecha: {g.fecha}."
    )


async def _poblar(session) -> int:
    embedding_service = EmbeddingService()
    repo = ExpenseRepository(session, FAMILIA_ID)

    gastos = (
        session.query(ExpenseTable)
        .filter(
            ExpenseTable.familia_id == FAMILIA_ID,
            ExpenseTable.notas == "seed_test",
            ExpenseTable.embedding.is_(None),
        )
        .order_by(ExpenseTable.fecha)
        .all()
    )

    if not gastos:
        print("  ✓  Todos los gastos ya tienen embedding.")
        return 0

    print(f"  📦 Generando embeddings para {len(gastos)} gastos en expenses.embedding...")
    ok_count = 0

    for g in gastos:
        texto = _formatear_gasto(g)
        result = await embedding_service.generar_embedding(texto)
        if hasattr(result, "ok") and result.ok():
            repo.guardar_embedding(g.id, result.ok())
            ok_count += 1
            print(f"  ✅ [{ok_count:02d}/{len(gastos)}] {g.fecha} | {g.descripcion[:45]}")
        else:
            print(f"  ❌ Error embedding: {g.descripcion} — {result}")

    return ok_count


def run(db):
    session = get_session()
    try:
        total = asyncio.run(_poblar(session))
        print(f"\n  🔍 {total} embeddings guardados en expenses.embedding para familia_id={FAMILIA_ID}")
    except Exception as e:
        session.rollback()
        print(f"  ❌ Error en seed de embeddings: {e}")
        raise
    finally:
        session.close()
