"""
Migration: add_exchange_rates
Created at: 2026-04-30T00:45:00
Adds exchange rate tracking table for USD/UYU daily quotes.
"""


def up(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS exchange_rates (
            id SERIAL PRIMARY KEY,
            currency_pair VARCHAR(10) NOT NULL DEFAULT 'USD/UYU',
            rate NUMERIC(10, 4) NOT NULL,
            date DATE NOT NULL DEFAULT CURRENT_DATE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_exchange_rate_date UNIQUE (date)
        )
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_exchange_rate_date
            ON exchange_rates(date DESC)
    """)


def down(db):
    db.execute("DROP TABLE IF EXISTS exchange_rates")
