"""
Migration: add_independent_details
Created at: 2026-09-05T00:00:00.000000
"""


def up(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS independent_details (
            id SERIAL PRIMARY KEY,
            economic_activity_id INTEGER NOT NULL UNIQUE
                REFERENCES economic_activities(id) ON DELETE CASCADE,
            regime VARCHAR(50) NOT NULL DEFAULT 'monotributo',
            pension_fund VARCHAR(50) NULL DEFAULT 'bps',
            estimated_monthly_gross_sales NUMERIC(12, 2) NULL,
            partner_count INTEGER NULL DEFAULT 1,
            employees_count INTEGER NOT NULL DEFAULT 0,
            has_mides_certificate BOOLEAN NULL DEFAULT FALSE,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        )
    """)


def down(db):
    db.execute("DROP TABLE IF EXISTS independent_details")
