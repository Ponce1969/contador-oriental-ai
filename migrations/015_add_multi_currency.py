"""
Migration: add_multi_currency
Created at: 2026-07-30T00:00:00
Adds currency column to monetary tables for USD/UYU support.
"""


def up(db):
    db.execute("""
        ALTER TABLE expenses
            ADD COLUMN IF NOT EXISTS currency VARCHAR(3) NOT NULL DEFAULT 'UYU'
    """)
    db.execute("""
        ALTER TABLE incomes
            ADD COLUMN IF NOT EXISTS currency VARCHAR(3) NOT NULL DEFAULT 'UYU'
    """)
    db.execute("""
        ALTER TABLE installment_purchases
            ADD COLUMN IF NOT EXISTS currency VARCHAR(3) NOT NULL DEFAULT 'UYU'
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_expenses_familia_currency
            ON expenses(familia_id, currency)
    """)


def down(db):
    db.execute("""
        ALTER TABLE installment_purchases
            DROP COLUMN IF EXISTS currency
    """)
    db.execute("""
        ALTER TABLE incomes
            DROP COLUMN IF EXISTS currency
    """)
    db.execute("""
        ALTER TABLE expenses
            DROP COLUMN IF EXISTS currency
    """)
