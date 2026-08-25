"""
Migration: add_household_tables
Created at: 2026-08-06T19:18:51.593442
"""


def up(db):
    db.execute("""
        CREATE TABLE hogares (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'active',
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    db.execute("""
        CREATE TABLE household_members (
            id SERIAL PRIMARY KEY,
            household_id INTEGER NOT NULL REFERENCES hogares(id) ON DELETE CASCADE,
            familia_id INTEGER NOT NULL REFERENCES familias(id) ON DELETE CASCADE,
            role VARCHAR(20) NOT NULL,
            joined_at TIMESTAMP NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_household_member
                UNIQUE (household_id, familia_id)
        )
    """)
    db.execute("""
        CREATE TABLE household_invitations (
            id SERIAL PRIMARY KEY,
            household_id INTEGER NOT NULL REFERENCES hogares(id) ON DELETE CASCADE,
            token VARCHAR(64) UNIQUE NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            expires_at TIMESTAMP NOT NULL,
            accepted_by_familia_id INTEGER REFERENCES familias(id) ON DELETE SET NULL,
            accepted_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    db.execute("""
        CREATE TABLE shared_expense_links (
            id SERIAL PRIMARY KEY,
            household_id INTEGER NOT NULL REFERENCES hogares(id) ON DELETE CASCADE,
            gasto_id INTEGER NOT NULL REFERENCES expenses(id) ON DELETE CASCADE,
            familia_id INTEGER NOT NULL REFERENCES familias(id) ON DELETE CASCADE,
            linked_at TIMESTAMP NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_household_gasto_link UNIQUE (household_id, gasto_id)
        )
    """)
    db.execute("""
        CREATE TABLE household_settlements (
            id SERIAL PRIMARY KEY,
            household_id INTEGER NOT NULL REFERENCES hogares(id) ON DELETE RESTRICT,
            payer_familia_id INTEGER NOT NULL
                REFERENCES familias(id) ON DELETE RESTRICT,
            recipient_familia_id INTEGER NOT NULL
                REFERENCES familias(id) ON DELETE RESTRICT,
            monto DECIMAL(12,2) NOT NULL,
            fecha DATE NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    db.execute("""
        CREATE TABLE household_audit_log (
            id SERIAL PRIMARY KEY,
            household_id INTEGER NOT NULL REFERENCES hogares(id) ON DELETE CASCADE,
            familia_id INTEGER NOT NULL REFERENCES familias(id) ON DELETE CASCADE,
            gasto_id INTEGER NOT NULL,
            action VARCHAR(20) NOT NULL,
            timestamp TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    # Indexes
    db.execute("CREATE INDEX idx_hogares_status ON hogares(status)")
    db.execute(
        "CREATE INDEX idx_household_members_familia ON household_members(familia_id)"
    )
    db.execute(
        """
        CREATE INDEX idx_household_members_household
        ON household_members(household_id)
    """
    )
    db.execute("CREATE INDEX idx_invitations_token ON household_invitations(token)")
    db.execute(
        """
        CREATE INDEX idx_invitations_household_status
        ON household_invitations(household_id, status)
    """
    )
    db.execute(
        "CREATE INDEX idx_shared_links_household ON shared_expense_links(household_id)"
    )
    db.execute(
        "CREATE INDEX idx_shared_links_familia ON shared_expense_links(familia_id)"
    )
    db.execute("CREATE INDEX idx_shared_links_gasto ON shared_expense_links(gasto_id)")
    db.execute(
        "CREATE INDEX idx_settlements_household ON household_settlements(household_id)"
    )
    db.execute(
        "CREATE INDEX idx_settlements_payer ON household_settlements(payer_familia_id)"
    )
    db.execute(
        """
        CREATE INDEX idx_settlements_recipient
        ON household_settlements(recipient_familia_id)
    """
    )
    db.execute(
        """
        CREATE INDEX idx_settlements_fecha
        ON household_settlements(household_id, fecha)
    """
    )
    db.execute(
        "CREATE INDEX idx_audit_log_household ON household_audit_log(household_id)"
    )
    db.execute("CREATE INDEX idx_audit_log_familia ON household_audit_log(familia_id)")


def down(db):
    db.execute("DROP TABLE IF EXISTS household_audit_log CASCADE")
    db.execute("DROP TABLE IF EXISTS household_settlements CASCADE")
    db.execute("DROP TABLE IF EXISTS shared_expense_links CASCADE")
    db.execute("DROP TABLE IF EXISTS household_invitations CASCADE")
    db.execute("DROP TABLE IF EXISTS household_members CASCADE")
    db.execute("DROP TABLE IF EXISTS hogares CASCADE")
