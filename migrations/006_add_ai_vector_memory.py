"""
Migración 006: add_ai_vector_memory
Despierta las capacidades vectoriales de PostgreSQL para el Contador Oriental.
Crea la infraestructura para búsqueda semántica con pgvector y HNSW.

Integra con estructura existente (VERIFICADA):
- familias (id, nombre, email, activo, created_at)
- usuarios (id, familia_id, username, password_hash, nombre_completo, activo, created_at, last_login)
- family_members (id, familia_id, nombre, ...)
- incomes (id, familia_id, family_member_id, monto, fecha, descripcion, categoria, es_recurrente, frecuencia, notas, tipo_ingreso)
- expenses (id, familia_id, monto, fecha, descripcion, categoria, subcategoria, metodo_pago, es_recurrente, frecuencia, notas, name, price, category, purchased, purchase_date)
- monthly_expense_snapshots (id, familia_id, anio, mes, categoria, total_dinero, cantidad_compras, ticket_promedio, created_at)
"""
from sqlalchemy import text


def up(conn):
    """Crear tabla de memoria vectorial con pgvector y HNSW optimizado"""
    print("🧠 Preparando cerebro vectorial en PostgreSQL...")

    # 1. Habilitar la extensión pgvector (necesita privilegios de superusuario)
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

    # 2. Crear la tabla de memoria IA
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ai_vector_memory (
            id SERIAL PRIMARY KEY,
            familia_id INTEGER NOT NULL REFERENCES familias(id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            embedding vector(768),
            source_type VARCHAR(50),
            source_id INTEGER,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """))

    # 3. Índice HNSW optimizado para Orange Pi 5 Plus (RAM eficiente)
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_ai_vector_memory_embedding
        ON ai_vector_memory
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    """))

    # 4. Índice por familia_id para multitenancy eficiente
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_ai_vector_memory_familia
        ON ai_vector_memory (familia_id);
    """))

    print("✅ Migración 006 completada: pgvector y tabla ai_vector_memory listas.")


def down(conn):
    """Eliminar tabla de memoria vectorial"""
    conn.execute(text("DROP TABLE IF EXISTS ai_vector_memory;"))
    print("🗑️ Memoria IA eliminada.")
