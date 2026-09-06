"""
Migration: add_entorno_to_expenses_and_incomes
Created at: 2026-09-05T21:35:00
Adds entorno column to expenses and incomes for Hogar / Campo context support.
"""


def up(db):
    db.execute("""
        ALTER TABLE expenses
            ADD COLUMN IF NOT EXISTS entorno VARCHAR(20) NOT NULL DEFAULT 'hogar'
    """)
    db.execute("""
        ALTER TABLE incomes
            ADD COLUMN IF NOT EXISTS entorno VARCHAR(20) NOT NULL DEFAULT 'hogar'
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_expenses_familia_entorno
            ON expenses(familia_id, entorno)
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_incomes_familia_entorno
            ON incomes(familia_id, entorno)
    """)


def down(db):
    db.execute("""
        DROP INDEX IF EXISTS idx_incomes_familia_entorno
    """)
    db.execute("""
        DROP INDEX IF EXISTS idx_expenses_familia_entorno
    """)
    db.execute("""
        ALTER TABLE incomes
            DROP COLUMN IF EXISTS entorno
    """)
    db.execute("""
        ALTER TABLE expenses
            DROP COLUMN IF EXISTS entorno
    """)
