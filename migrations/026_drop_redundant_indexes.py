"""
Migration: drop_redundant_indexes
Created at: 2026-09-18
Drops 10 redundant indexes identified by PostgresHealthAuditor.
"""


def _exec(db, stmt: str) -> None:
    try:
        from sqlalchemy import text

        db.execute(text(stmt))
    except Exception:
        db.execute(stmt)


def up(db):
    """Drop 10 redundant indexes whose prefixes/uniques are already covered."""
    # 1. monthly_expense_snapshots:
    # covered by monthly_expense_snapshots_familia_id_anio_mes_categoria_key
    _exec(db, "DROP INDEX IF EXISTS idx_snapshots_familia_periodo")

    # 2. password_reset_tokens:
    # covered by password_reset_tokens_token_key (UNIQUE constraint)
    _exec(db, "DROP INDEX IF EXISTS idx_password_reset_tokens_token")

    # 3. installment_payments:
    # covered by uq_installment_number (installment_purchase_id, numero_cuota)
    _exec(db, "DROP INDEX IF EXISTS idx_payments_purchase")

    # 4. installment_purchases:
    # covered by idx_installments_activo (familia_id, activo)
    _exec(db, "DROP INDEX IF EXISTS idx_installments_familia")

    # 5. exchange_rates:
    # covered by uq_exchange_rate_date (date)
    _exec(db, "DROP INDEX IF EXISTS idx_exchange_rate_date")

    # 6. ai_usage:
    # covered by uq_ai_usage_daily (familia_id, date, model)
    _exec(db, "DROP INDEX IF EXISTS idx_ai_usage_lookup")

    # 7. household_members:
    # covered by uq_household_member (household_id, user_id/familia_id)
    _exec(db, "DROP INDEX IF EXISTS idx_household_members_household")

    # 8. household_invitations:
    # covered by household_invitations_token_key (UNIQUE constraint)
    _exec(db, "DROP INDEX IF EXISTS idx_invitations_token")

    # 9. shared_expense_links:
    # covered by uq_household_gasto_link (household_id, gasto_id)
    _exec(db, "DROP INDEX IF EXISTS idx_shared_links_household")

    # 10. household_settlements:
    # covered by idx_settlements_fecha (household_id, fecha)
    _exec(db, "DROP INDEX IF EXISTS idx_settlements_household")


def down(db):
    """Recreate the 10 indexes in case of rollback."""
    _exec(
        db,
        """
        CREATE INDEX IF NOT EXISTS idx_snapshots_familia_periodo
            ON monthly_expense_snapshots(familia_id, anio, mes)
        """,
    )
    _exec(
        db,
        """
        CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token
            ON password_reset_tokens(token)
        """,
    )
    _exec(
        db,
        """
        CREATE INDEX IF NOT EXISTS idx_payments_purchase
            ON installment_payments(installment_purchase_id)
        """,
    )
    _exec(
        db,
        """
        CREATE INDEX IF NOT EXISTS idx_installments_familia
            ON installment_purchases(familia_id)
        """,
    )
    _exec(
        db,
        """
        CREATE INDEX IF NOT EXISTS idx_exchange_rate_date
            ON exchange_rates(date DESC)
        """,
    )
    _exec(
        db,
        """
        CREATE INDEX IF NOT EXISTS idx_ai_usage_lookup
            ON ai_usage(familia_id, date)
        """,
    )
    _exec(
        db,
        """
        CREATE INDEX IF NOT EXISTS idx_household_members_household
            ON household_members(household_id)
        """,
    )
    _exec(
        db,
        """
        CREATE INDEX IF NOT EXISTS idx_invitations_token
            ON household_invitations(token)
        """,
    )
    _exec(
        db,
        """
        CREATE INDEX IF NOT EXISTS idx_shared_links_household
            ON shared_expense_links(household_id)
        """,
    )
    _exec(
        db,
        """
        CREATE INDEX IF NOT EXISTS idx_settlements_household
            ON household_settlements(household_id)
        """,
    )


# Aliases for compatibility with different runners
upgrade = up
downgrade = down
