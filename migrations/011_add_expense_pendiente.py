"""
Migration: add_expense_pendiente
Flag para gastos auto-generados por cuotas
"""


def up(db):
    db.execute("""
        ALTER TABLE expenses
            ADD COLUMN IF NOT EXISTS pendiente BOOLEAN NOT NULL DEFAULT FALSE
    """)


def down(db):
    db.execute("ALTER TABLE expenses DROP COLUMN IF EXISTS pendiente")
