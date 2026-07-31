# Multi-Currency Migration Specification

## Purpose
Defines the additive migration `015_add_multi_currency.py` and its rollback behavior, including the accepted risk that rollback destroys USD currency information.

## ADDED Requirements

### Requirement: Migration 015 adds currency column to three tables
The migration MUST add a `currency VARCHAR(3) NOT NULL DEFAULT 'UYU'` column to `expenses`, `incomes`, and `installment_purchases` only. It MUST NOT add the column to `installment_payments`. The migration MUST use the `fleting` CLI framework (`up(db)`/`down(db)` with raw SQL via `db.execute`), not Alembic.

#### Scenario: Up applies to three tables
- GIVEN migration `015` runs via `fleting db migrate`
- WHEN `up(db)` executes
- THEN `expenses`, `incomes`, and `installment_purchases` MUST each gain a `currency` column
- AND existing rows MUST have `currency = 'UYU'` from the server default
- AND `installment_payments` MUST NOT gain a `currency` column

#### Scenario: No backfill required
- GIVEN existing rows before migration
- WHEN `up(db)` runs
- THEN PostgreSQL applies the constant default atomically
- AND no separate backfill `UPDATE` SHALL be REQUIRED

### Requirement: Migration is tracked in _fleting_migrations
The migration MUST be tracked in the `_fleting_migrations` table so `fleting db status` reflects it and `fleting db rollback` can select it.

#### Scenario: Status shows migration
- GIVEN migration `015` has applied successfully
- WHEN `fleting db status` runs
- THEN migration `015` MUST appear as applied

### Requirement: Rollback drops the currency column
`down(db)` MUST drop the `currency` column from `expenses`, `incomes`, and `installment_purchases`. The rollback MUST be executable via `fleting db rollback`.

#### Scenario: Rollback drops columns cleanly
- GIVEN migration `015` is applied and only UYU rows exist
- WHEN `fleting db rollback` runs
- THEN the `currency` column MUST be dropped from the three tables
- AND no data loss occurs for UYU-only families

### Requirement: Rollback destroys USD currency information (accepted risk)
If any row has `currency != 'UYU'` at rollback time, rolling back migration `015` DOES NOT preserve the UYU/USD distinction. Amounts survive but their currency context is lost. v1 accepts this risk and documents it.

#### Scenario: Rollback with USD records
- GIVEN USD rows exist before rollback
- WHEN `down(db)` drops the `currency` column
- THEN the amounts survive but their USD currency information is lost
- AND recovery requires a re-migration with backfill, which is out of scope for v1

### Requirement: Optional supporting index
The migration MAY create `idx_expenses_familia_currency` to speed per-currency, tenant-scoped queries. The index is not required for correctness.

#### Scenario: Index optional
- GIVEN the migration runs
- WHEN the index is created
- THEN per-currency expense queries SHOULD benefit
- AND its absence MUST NOT cause incorrect results

### Requirement: Formatters remain backward compatible across phases
Formatters keep the default `currency="UYU"`, so reverting later phases (services, views, AI) MUST NOT break existing call sites even before reverting the migration.

#### Scenario: Partial revert safe
- GIVEN migration `015` is applied but the dashboard reverts to single-currency code
- WHEN the dashboard runs
- THEN the unchanged `format_pesos` call sites continue to work because of the `"UYU"` default