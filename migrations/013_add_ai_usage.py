"""
Migration: add_ai_usage
Created at: 2026-05-01
Adds ai_usage table for tracking daily Llama 3 query quotas per family.
"""


def up(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS ai_usage (
            id SERIAL PRIMARY KEY,
            familia_id INTEGER NOT NULL REFERENCES familias(id),
            date DATE NOT NULL DEFAULT CURRENT_DATE,
            model VARCHAR(20) NOT NULL,
            prompt_tokens INTEGER NOT NULL DEFAULT 0,
            completion_tokens INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_ai_usage_daily UNIQUE (familia_id, date, model)
        )
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_ai_usage_lookup
            ON ai_usage(familia_id, date)
    """)


def down(db):
    db.execute("DROP TABLE IF EXISTS ai_usage")