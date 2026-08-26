"""
Migration: add_savings_goals
Created at: 2026-08-26T20:30:00.000000
"""


def up(db):
    # 1. Tabla de metas de ahorro familiares
    db.execute("""
        CREATE TABLE IF NOT EXISTS savings_goals (
            id SERIAL PRIMARY KEY,
            familia_id INTEGER NOT NULL REFERENCES familias(id) ON DELETE CASCADE,
            name VARCHAR(120) NOT NULL,
            target_amount NUMERIC(12, 2) NOT NULL,
            currency VARCHAR(3) NOT NULL DEFAULT 'UYU',
            current_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
            deadline DATE NULL,
            category VARCHAR(50) NOT NULL DEFAULT 'general',
            icon VARCHAR(50) NOT NULL DEFAULT 'savings',
            color VARCHAR(30) NOT NULL DEFAULT '#6200EE',
            is_completed BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        )
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_savings_goals_familia 
        ON savings_goals (familia_id)
    """)

    # 2. Tabla de aportes / contribuciones a las metas
    db.execute("""
        CREATE TABLE IF NOT EXISTS savings_goal_contributions (
            id SERIAL PRIMARY KEY,
            savings_goal_id INTEGER NOT NULL 
                REFERENCES savings_goals(id) ON DELETE CASCADE,
            family_member_id INTEGER NULL 
                REFERENCES family_members(id) ON DELETE SET NULL,
            amount NUMERIC(12, 2) NOT NULL,
            currency VARCHAR(3) NOT NULL DEFAULT 'UYU',
            source_type VARCHAR(50) NOT NULL DEFAULT 'regular_income',
            note VARCHAR(255) NULL,
            fecha DATE NOT NULL DEFAULT CURRENT_DATE,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        )
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_goal_contributions_goal 
        ON savings_goal_contributions (savings_goal_id)
    """)


def down(db):
    db.execute("DROP TABLE IF EXISTS savings_goal_contributions CASCADE")
    db.execute("DROP TABLE IF EXISTS savings_goals CASCADE")
