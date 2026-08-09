"""
Migration: add_member_unlinked_at
Created at: 2026-08-09T19:00:00
Adds unlinked_at timestamp to family_members for soft-delete tracking.
"""


def up(db):
    db.execute("""
        ALTER TABLE family_members
        ADD COLUMN unlinked_at TIMESTAMP DEFAULT NULL
    """)


def down(db):
    db.execute("""
        ALTER TABLE family_members
        DROP COLUMN unlinked_at
    """)
