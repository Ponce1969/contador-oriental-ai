"""
Migration: add_password_recovery
Created at: 2026-06-13
Adds email column to usuarios and password_reset_tokens table for password recovery.
"""


def up(db):
    db.execute("""
        ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS email VARCHAR(100) UNIQUE
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            token VARCHAR(255) NOT NULL UNIQUE,
            expires_at TIMESTAMP NOT NULL,
            used_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token
            ON password_reset_tokens(token)
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user_id
            ON password_reset_tokens(user_id)
    """)


def down(db):
    db.execute("DROP TABLE IF EXISTS password_reset_tokens")
    db.execute("ALTER TABLE usuarios DROP COLUMN IF EXISTS email")
