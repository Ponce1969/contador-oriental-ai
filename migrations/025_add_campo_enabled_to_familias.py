"""
Migration: add_campo_enabled_to_familias
Created at: 2026-09-10T20:25:00.000000
Adds campo_enabled boolean column to familias table.
"""


def up(db):
    db.execute("""
        ALTER TABLE familias 
        ADD COLUMN IF NOT EXISTS campo_enabled BOOLEAN NOT NULL DEFAULT FALSE
    """)


def down(db):
    db.execute("""
        ALTER TABLE familias 
        DROP COLUMN IF EXISTS campo_enabled
    """)
