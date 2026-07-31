# Proposal: Multi-Currency Support for Expenses and Incomes

## Intent

Users in Uruguay regularly buy durables, cars, and imported goods in USD. Today the app only records a single peso amount, forcing users to manually convert the original USD figure and losing the real price they paid. This change lets each expense and income keep its original currency, starting with UYU and USD.

## Scope

### In Scope
- Domain models: add `currency` to `Expense`, `Income`, and `InstallmentPurchase`.
- SQLAlchemy tables: add `currency` to `expenses`, `incomes`, and `installment_purchases` only. `installment_payments` derives currency from the parent purchase via FK — no separate column.
- Mappers: pass `currency` between table rows and domain models.
- Formatters: add optional `currency` parameter (default `"UYU"`) to peso/utility formatters. Existing tests pass unchanged.
- Views: expenses/incomes form (currency dropdown + badge), dashboard (two per-currency balance cards), history (per-currency totals), planes (currency badge from purchase), summary renderer (per-currency filter).
- AI context builders: `agrupar_gastos()` groups by `(categoria, currency)`. `ai_advisor_service` per-currency formatting. `AIContext` gets per-currency totals. **The AI system prompt at `ai_advisor_service.py:420-424` must be revised** — the current rules "total mensual SIEMPRE en $" and "USD solo para contextualizar" are incompatible with multi-currency and would confuse the model.
- Report service: per-currency totals and row formatting.
- Controllers and services: totals return per-currency or accept a currency filter.
- OCR: add optional `currency` field to parsed ticket JSON, defaulting to `"UYU"` when undetected.
- Seeds: explicit `currency="UYU"` + optional USD seed examples.
- Migration `migrations/015_add_multi_currency.py` (`fleting` custom CLI, `up(db)`/`down(db)` with raw SQL).
- Tests: extended (not rewritten) with USD cases for formatters, models, aggregation, and installments.

### Out of Scope
- Conversion math between currencies.
- Historical exchange-rate storage per transaction. The existing `exchange_rates` table (daily USD/UYU rates) remains available for future use but is NOT used for transaction conversion in v1.
- UI for currencies beyond UYU/USD (though the schema supports them).
- Any change to embeddings or the vector store (`expenses.embedding` depends on description/monto text, not a currency column).
- `currency` column on `installment_payments` — payments derive currency from the parent purchase.

## Capabilities

### New Capabilities
- `multi-currency`: record and display expenses and incomes in their original currency.
- `per-currency-aggregation`: compute and present totals grouped by currency, never mixing UYU and USD.
- `ocr-currency-detection`: parse currency from tickets with UYU fallback.

### Modified Capabilities
None — `openspec/specs/` is empty; the affected behaviors are new capabilities.

## Business Rules
1. v1 shows each currency separately, never converted. Dashboard and reports display independent UYU and USD balances.
2. `currency` is a `String(3)` with `server_default='UYU'`, not an enum. UYU/USD are supported now; EUR/BRL/etc. can be added later without a migration.
3. OCR parsing attempts to detect USD when Gemma sees it; otherwise it defaults to UYU. This is a soft enhancement, not a v1 blocker.
4. Dashboard shows two balance cards side by side: UYU and USD.
5. Historical exchange-rate storage is deferred to v2. v1 does not store per-transaction rate. The existing `exchange_rates` table (daily USD/UYU) is not used for conversion.
6. The AI model receives per-currency pre-calculated data and never performs financial calculations. The system prompt is revised so it no longer says "total mensual SIEMPRE en $" nor treats USD as "solo para contextualizar."
7. `monto` remains `Decimal`; `currency` represents the currency of that amount. Original values are preserved, never silently converted.

## Approach

Approach A: add a `currency` column to `expenses`, `incomes`, and `installment_purchases` tables, and group all aggregations by currency. Domain models, mappers, formatters, views, controllers, services, AI context, reports, and OCR are updated to carry and respect the currency field.

Approach B (separate `monto_uyu`/`monto_usd` columns) was rejected because it wastes a column for almost every row, makes SUM queries awkward, and breaks normal form. Approach C (store everything in UYU and display in USD on demand) was rejected because it loses the original USD amount and becomes inaccurate when rates change.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `models/expense_model.py` | Modified | Add `currency: str = "UYU"` field. |
| `models/income_model.py` | Modified | Add `currency: str = "UYU"` field. |
| `models/installment_model.py` | Modified | Add `currency: str = "UYU"` to `InstallmentPurchase`. |
| `models/ai_model.py` | Modified | Per-currency totals in `AIContext`. |
| `database/tables.py` | Modified | Add `currency` to expenses, incomes, installment_purchases. NOT to installment_payments. |
| `migrations/015_add_multi_currency.py` | New | `fleting` migration; `up(db)`: ADD COLUMN currency on 3 tables with DEFAULT 'UYU'; `down(db)`: DROP COLUMN. |
| `repositories/mappers.py` | Modified | Map `currency` for expenses. |
| `repositories/income_mappers.py` | Modified | Map `currency` for incomes. |
| `utils/formatters.py` | Modified | Optional `currency` parameter (default `"UYU"`). |
| `services/infrastructure/formatters.py` | Modified | Optional `currency` parameter to `format_pesos`/`format_pesos_ai`. |
| `views/pages/expenses_view.py` | Modified | Currency dropdown and badges. |
| `views/pages/incomes_view.py` | Modified | Currency dropdown and badges. |
| `views/pages/dashboard_view.py` | Modified | Two per-currency balance cards. |
| `views/pages/history_view.py` | Modified | Per-currency totals. |
| `views/pages/planes_view.py` | Modified | Currency badge from InstallmentPurchase. |
| `views/components/summary_renderer.py` | Modified | Per-currency rendering/filtering. |
| `services/ai/expense_formatters.py` | Modified | Group by `(categoria, currency)`. |
| `services/ai/ai_advisor_service.py` | Modified | Per-currency totals in prompts; system prompt revised (lines 420-424). |
| `services/infrastructure/report_service.py` | Modified | Per-currency totals and row formatting. |
| `controllers/expense_controller.py` | Modified | Totals return per-currency or accept currency filter. |
| `controllers/income_controller.py` | Modified | Same. |
| `controllers/history_controller.py` | Modified | Same. |
| `controllers/installment_controller.py` | Modified | `generar_gastos_programados` propagates `plan.currency` to generated `Expense`. |
| `services/domain/expense_service.py` | Modified | Totals accept `currency` parameter. |
| `services/domain/income_service.py` | Modified | Same. |
| `ocr_api/main.py` | Modified | Optional `currency` in JSON prompt schema (lines 40-58). |
| `seeds/001_gastos_ficticios.py` | Modified | Explicit `currency="UYU"`; optional USD examples. |
| `tests/test_formatters.py` | Modified | USD test cases. |
| `tests/test_ai_formatters.py` | Modified | USD test cases. |

## Edge Cases

- Mixed-currency family: dashboard must not sum UYU and USD; each currency is independent.
- Installment purchases: generated `Expense` records must inherit `plan.currency`; `installment_payments` derive currency from the parent purchase — no separate column.
- Seed data: existing seeds must be explicit about UYU and include a few USD examples.
- OCR ambiguous currency: receipt parsing defaults to UYU when unsure.
- AI must not calculate: the existing "NUNCA hacer cálculos" instruction remains in force. The prompt is revised so the model no longer assumes single-currency totals.
- Rollback with USD data: if USD records exist, rolling back drops the `currency` column and loses that distinction (amounts survive but become ambiguous). Acceptable risk for v1.

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Dashboard dual-card layout breaks small screens | Medium | Keep cards in a responsive row; test on mobile. |
| `summary_renderer` signature change breaks callers | Low | Add optional `currency` parameter; existing signatures unchanged. |
| ~100 existing formatter assertions break | Low | Default `currency="UYU"` keeps all existing output. Tests extended, not rewritten. |
| AI prompt misinterprets USD amounts | Medium | Revise system prompt (lines 420-424) from single-currency to per-currency rules. Keep "NUNCA hacer cálculos." |
| Installment expenses lose currency | Low | `currency` on `InstallmentPurchase`; `generar_gastos_programados` copies it to each generated `Expense`. |
| Rollback loses USD currency info | Low | Documented caveat. v1 accepts risk; re-migration needed for recovery. |

## Rollback Plan

Migration `015` uses the `fleting` CLI: `fleting db rollback` executes `down(db)`, which drops the new `currency` columns from `expenses`, `incomes`, and `installment_purchases`.

**Caveat**: If USD records are created after migration, rolling back **destroys** that currency information (amounts survive, but the UYU/USD distinction is lost). No data is permanently destroyed at the migration level for UYU-only families. For families with USD records, proper rollback requires a re-migration (re-adding the column with a backfill), which is out of scope for v1.

Formatters keep the default `currency="UYU"`, so reverting later phases does not break existing call sites.

## Dependencies

- `fleting` CLI migration system (`up(db)`/`down(db)` with `db.execute`, tracked in `_fleting_migrations` table). Pattern from existing migrations: `001_initial.py` through `014_add_password_recovery.py`.
- Existing `ExchangeRateService` and `exchange_rates` table remain **unchanged** and available for future conversion functionality. They are NOT used for transaction conversion in v1.
- `SQLAlchemy` for `mapped_column(String(3))`.
- `PostgreSQL 16` — supports `ADD COLUMN ... DEFAULT 'UYU'` with atomic default propagation (no table rewrite for constant default).

## Success Criteria

- [ ] A user can create an expense in USD, and it is saved and displayed as `USD NNN.NN`.
- [ ] Dashboard shows two independent balance cards: "Balance UYU: $ X" and "Balance USD: USD Y".
- [ ] All existing tests pass without rewriting existing assertions (currency param defaults to `"UYU"`).
- [ ] Income, history, planes, reports, AI context, and `agrupar_gastos()` all respect per-currency grouping.
- [ ] The AI system prompt no longer says "total mensual SIEMPRE en $"; it reports per-currency totals.
- [ ] OCR defaults to `"UYU"` when currency is ambiguous; accepts `"USD"` when Gemma detects it.
- [ ] Migration `015` applies and rolls back via `fleting db promote`/`fleting db rollback`.
- [ ] No sum of `UYU + USD` occurs anywhere — all aggregations filter or group by currency.
- [ ] `generar_gastos_programados()` correctly propagates `InstallmentPurchase.currency` to generated `Expense` records.
- [ ] New tests cover: Expense UYU, Expense USD, Income UYU, Income USD, mixed-currency aggregation prevention, installments with USD, formatter UYU, formatter USD, OCR currency detection and fallback.

## Next Phases

Ready for `sdd-spec` and `sdd-design` (can run in parallel), then `sdd-tasks`.
