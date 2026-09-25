"""
Migration: add_unindexed_foreign_key_indexes
Created at: 2026-09-24
Creates secondary B-Tree indexes for 10 unindexed foreign keys
identified by PostgresHealthAuditor.
"""


def _exec(db, stmt: str) -> None:
    try:
        from sqlalchemy import text

        db.execute(text(stmt))
    except Exception:
        db.execute(stmt)


def up(db):
    """Create B-Tree indexes covering unindexed foreign keys."""
    # 1. economic_activities.family_member_id -> family_members(id) [CASCADE]
    _exec(
        db,
        """
        CREATE INDEX IF NOT EXISTS idx_economic_activities_family_member_id
            ON economic_activities (family_member_id)
        """,
    )

    # 2. expenses.installment_purchase_id -> installment_purchases(id) [SET NULL]
    _exec(
        db,
        """
        CREATE INDEX IF NOT EXISTS idx_expenses_installment_purchase_id
            ON expenses (installment_purchase_id)
        """,
    )

    # 3. household_invitations.accepted_by_familia_id -> familias(id) [SET NULL]
    _exec(
        db,
        """
        CREATE INDEX IF NOT EXISTS idx_household_invitations_accepted_by_familia_id
            ON household_invitations (accepted_by_familia_id)
        """,
    )

    # 4. incomes.economic_activity_id -> economic_activities(id) [SET NULL]
    _exec(
        db,
        """
        CREATE INDEX IF NOT EXISTS idx_incomes_economic_activity_id
            ON incomes (economic_activity_id)
        """,
    )

    # 5. incomes.family_member_id -> family_members(id)
    _exec(
        db,
        """
        CREATE INDEX IF NOT EXISTS idx_incomes_family_member_id
            ON incomes (family_member_id)
        """,
    )

    # 6. installment_payments.expense_id -> expenses(id)
    _exec(
        db,
        """
        CREATE INDEX IF NOT EXISTS idx_installment_payments_expense_id
            ON installment_payments (expense_id)
        """,
    )

    # 7. installment_payments.familia_id -> familias(id)
    _exec(
        db,
        """
        CREATE INDEX IF NOT EXISTS idx_installment_payments_familia_id
            ON installment_payments (familia_id)
        """,
    )

    # 8. installment_purchases.expense_id -> expenses(id)
    _exec(
        db,
        """
        CREATE INDEX IF NOT EXISTS idx_installment_purchases_expense_id
            ON installment_purchases (expense_id)
        """,
    )

    # 9. savings_goal_contributions.family_member_id -> family_members(id) [SET NULL]
    _exec(
        db,
        """
        CREATE INDEX IF NOT EXISTS idx_savings_contributions_family_member_id
            ON savings_goal_contributions (family_member_id)
        """,
    )

    # 10. usuarios.familia_id -> familias(id)
    _exec(
        db,
        """
        CREATE INDEX IF NOT EXISTS idx_usuarios_familia_id
            ON usuarios (familia_id)
        """,
    )


def down(db):
    """Drop the 10 foreign key indexes on rollback."""
    _exec(db, "DROP INDEX IF EXISTS idx_economic_activities_family_member_id")
    _exec(db, "DROP INDEX IF EXISTS idx_expenses_installment_purchase_id")
    _exec(db, "DROP INDEX IF EXISTS idx_household_invitations_accepted_by_familia_id")
    _exec(db, "DROP INDEX IF EXISTS idx_incomes_economic_activity_id")
    _exec(db, "DROP INDEX IF EXISTS idx_incomes_family_member_id")
    _exec(db, "DROP INDEX IF EXISTS idx_installment_payments_expense_id")
    _exec(db, "DROP INDEX IF EXISTS idx_installment_payments_familia_id")
    _exec(db, "DROP INDEX IF EXISTS idx_installment_purchases_expense_id")
    _exec(db, "DROP INDEX IF EXISTS idx_savings_contributions_family_member_id")
    _exec(db, "DROP INDEX IF EXISTS idx_usuarios_familia_id")


upgrade = up
downgrade = down
