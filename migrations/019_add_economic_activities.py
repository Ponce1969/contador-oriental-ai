"""
Migration: add_economic_activities
Created at: 2026-08-17T22:25:00.000000
"""


def up(db):
    # 1. Modo de finanzas en familias
    db.execute("""
        ALTER TABLE familias 
        ADD COLUMN IF NOT EXISTS modo_finanzas VARCHAR(30) DEFAULT 'basic'
    """)

    # 2. Tabla de actividades económicas
    db.execute("""
        CREATE TABLE IF NOT EXISTS economic_activities (
            id SERIAL PRIMARY KEY,
            familia_id INTEGER NOT NULL REFERENCES familias(id) ON DELETE CASCADE,
            family_member_id INTEGER NOT NULL
                REFERENCES family_members(id) ON DELETE CASCADE,
            nature VARCHAR(50) NOT NULL DEFAULT 'dependiente',
            title VARCHAR(100) NOT NULL DEFAULT 'Comercio / Servicios',
            start_date DATE NULL,
            end_date DATE NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        )
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_economic_activities_member 
        ON economic_activities (familia_id, family_member_id)
    """)

    # 3. Tabla de detalles de dependientes
    db.execute("""
        CREATE TABLE IF NOT EXISTS dependent_details (
            id SERIAL PRIMARY KEY,
            economic_activity_id INTEGER NOT NULL UNIQUE
                REFERENCES economic_activities(id) ON DELETE CASCADE,
            remuneration_type VARCHAR(30) NOT NULL DEFAULT 'mensual',
            weekly_hours INTEGER NOT NULL DEFAULT 40,
            estimated_monthly_nominal NUMERIC(12, 2) NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        )
    """)

    # 4. Campos en incomes
    db.execute("""
        ALTER TABLE incomes 
        ADD COLUMN IF NOT EXISTS concept VARCHAR(50) NULL
    """)
    db.execute("""
        ALTER TABLE incomes 
        ADD COLUMN IF NOT EXISTS economic_activity_id INTEGER
        REFERENCES economic_activities(id) ON DELETE SET NULL
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_incomes_concept 
        ON incomes (familia_id, concept)
    """)

    # 5. Mapeo seguro de datos históricos de ingresos existentes
    db.execute("""
        UPDATE incomes 
        SET concept = 'salary' 
        WHERE categoria LIKE '%Sueldo%' AND concept IS NULL
    """)


def down(db):
    db.execute("DROP INDEX IF EXISTS idx_incomes_concept")
    db.execute("ALTER TABLE incomes DROP COLUMN IF NOT EXISTS economic_activity_id")
    db.execute("ALTER TABLE incomes DROP COLUMN IF NOT EXISTS concept")
    db.execute("DROP TABLE IF EXISTS dependent_details")
    db.execute("DROP INDEX IF EXISTS idx_economic_activities_member")
    db.execute("DROP TABLE IF EXISTS economic_activities")
    db.execute("ALTER TABLE familias DROP COLUMN IF NOT EXISTS modo_finanzas")
