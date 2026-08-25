"""
Migration: add_requests_count_to_ai_usage
Created at: 2026-08-23T21:20:00.000000
Adds requests_count column to ai_usage table to align with AiUsageTable definition.
"""


def up(db):
    db.execute("""
        ALTER TABLE ai_usage
        ADD COLUMN IF NOT EXISTS requests_count INTEGER NOT NULL DEFAULT 1
    """)


def down(db):
    db.execute("""
        ALTER TABLE ai_usage
        DROP COLUMN IF EXISTS requests_count
    """)
