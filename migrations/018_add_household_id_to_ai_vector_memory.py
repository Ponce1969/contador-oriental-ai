"""
Migration: add_household_id_to_ai_vector_memory
Created at: 2026-08-06T19:19:03.508714
"""


def up(db):
    db.execute("""
        ALTER TABLE ai_vector_memory
        ADD COLUMN IF NOT EXISTS household_id INTEGER
        REFERENCES hogares(id) ON DELETE CASCADE
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_ai_vector_memory_household
        ON ai_vector_memory (household_id)
        WHERE household_id IS NOT NULL
    """)


def down(db):
    db.execute("DROP INDEX IF EXISTS idx_ai_vector_memory_household")
    db.execute("ALTER TABLE ai_vector_memory DROP COLUMN IF NOT EXISTS household_id")
