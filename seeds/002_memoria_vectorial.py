"""
Seed: poblar ai_vector_memory con embeddings de los gastos del seed anterior.
Llama a IAMemoryService directamente usando asyncio para generar embeddings reales
con nomic-embed-text vía Ollama.

Idempotente: borra registros con source_type='seed' antes de insertar.
"""

from __future__ import annotations

import asyncio
import logging
import os

from database.engine import get_session
from database.tables import ExpenseTable
from repositories.memoria_repository import MemoriaRepository
from services.ai.embedding_service import EmbeddingService
from services.ai.ia_memory_service import IAMemoryService

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

FAMILIA_ID = 3  # Cambiá si tu familia_id es diferente


def _formatear_gasto(g: ExpenseTable) -> str:
    """Genera el texto narrativo del gasto para vectorizar (mismo formato que MemoryEventHandler)."""
    return (
        f"Gasto registrado: {g.descripcion} "
        f"por ${g.monto:,.0f} "
        f"en categoría {g.categoria}. "
        f"Método: {g.metodo_pago}. "
        f"Fecha: {g.fecha}."
    )


async def _poblar(session) -> int:
    memoria_repo = MemoriaRepository(session, FAMILIA_ID)
    embedding_service = EmbeddingService()
    memory_service = IAMemoryService(memoria_repo, embedding_service)

    # Borrar embeddings previos del seed (idempotente)
    from sqlalchemy import text
    session.execute(
        text(
            "DELETE FROM ai_vector_memory "
            "WHERE familia_id = :fid AND source_type = 'seed'"
        ),
        {"fid": FAMILIA_ID},
    )
    session.commit()

    # Cargar todos los gastos del seed (marcados con notas='seed_test')
    gastos = (
        session.query(ExpenseTable)
        .filter(
            ExpenseTable.familia_id == FAMILIA_ID,
            ExpenseTable.notas == "seed_test",
        )
        .order_by(ExpenseTable.fecha)
        .all()
    )

    if not gastos:
        print("  ⚠️  No hay gastos del seed. Ejecutá primero: uv run fleting db seed")
        return 0

    print(f"  📦 Generando embeddings para {len(gastos)} gastos...")
    ok_count = 0

    for g in gastos:
        texto = _formatear_gasto(g)
        result = await memory_service.registrar_evento_contable(
            texto_plano=texto,
            source_type="seed",
            source_id=g.id,
        )
        if hasattr(result, "ok") and result.ok():
            ok_count += 1
            print(f"  ✅ [{ok_count:02d}/{len(gastos)}] {g.fecha} | {g.descripcion[:45]}")
        else:
            print(f"  ❌ Error embedding: {g.descripcion} — {result}")

    return ok_count


def run(db):
    """Entrada del CLI de Fleting. Ignora db (SQLite) y usa SQLAlchemy directo."""
    if os.getenv("APP_ENV") == "production":
        print("  ⛔ Seeds deshabilitados en APP_ENV=production. Abortando.")
        return
    session = get_session()
    try:
        total = asyncio.run(_poblar(session))
        print(f"\n  🧠 {total} embeddings guardados en ai_vector_memory para familia_id={FAMILIA_ID}")
    except Exception as e:
        session.rollback()
        print(f"  ❌ Error en seed vectorial: {e}")
        raise
    finally:
        session.close()
