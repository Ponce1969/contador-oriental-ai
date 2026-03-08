"""
Migration: agregar columna embedding vector(768) a la tabla expenses.
Permite búsqueda semántica cosine via pgvector para subtotales por descripción.
"""


def up(conn):
    conn.execute("""
        ALTER TABLE expenses
        ADD COLUMN IF NOT EXISTS embedding vector(768)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_expenses_embedding
        ON expenses
        USING hnsw (embedding vector_cosine_ops)
    """)


def down(conn):
    conn.execute("DROP INDEX IF EXISTS idx_expenses_embedding")
    conn.execute("ALTER TABLE expenses DROP COLUMN IF EXISTS embedding")
