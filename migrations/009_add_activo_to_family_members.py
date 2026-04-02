"""
Migration: add_activo_to_family_members
Created at: 2026-03-07T05:30:08.568228
"""


def up(db):
    from sqlalchemy import text

    db.execute(
        text(
            "ALTER TABLE family_members ADD COLUMN IF NOT EXISTS activo BOOLEAN DEFAULT TRUE"
        )
    )
    print("✅ Columna activo agregada a family_members")


def down(db):
    from sqlalchemy import text

    db.execute(text("ALTER TABLE family_members DROP COLUMN IF EXISTS activo"))
