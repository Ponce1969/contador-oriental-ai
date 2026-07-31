# Exploration: Multi-Currency (USD + UYU) for Expenses and Incomes

## Current State

The Contador Oriental is a single-currency app. Every monetary value flows through `monto: Decimal` described as "pesos" — from domain models to SQLAlchemy tables to formatters to views. The `ExchangeRateTable` and `ExchangeRateService` already exist (migration `012`, scheduler in `main.py:95`, live badge in `main_layout.py:207`), but they are **read-only display** — no expense or income references them. The `exchange_rates` table stores a daily USD/UYU rate (unique per date), but this historical data is unused in v1.

A critical inconsistency exists in the AI advisor prompt (`services/ai/ai_advisor_service.py:420-424`): it says "El total mensual SIEMPRE en $ (pesos)" and "Usá USD solo para contextualizar compras grandes o deudas en esa moneda." This makes sense only in a single-currency world. Once real USD expenses exist, these instructions would confuse the model. The prompt MUST be revised for multi-currency (not just the formatter calls).

Currency formatting is split across three formatter modules:
- `utils/formatters.py`: `format_currency` / `format_currency_with_symbol` — always `$ `
- `services/infrastructure/formatters.py`: `format_pesos` / `format_pesos_ai` / `format_cotizacion` — always `$ `
- No formatter accepts a currency parameter today.

## Affected Areas

### 1. Domain Models

| File | Change Needed |
|------|--------------|
| `models/expense_model.py:24` | Add `currency: str = "UYU"` field. Update `description` on `monto` from "pesos" to "amount". Update `__str__`. |
| `models/income_model.py:54` | Add `currency: str = "UYU"` field. Same description/`__str__` updates. |
| `models/installment_model.py:26` | Add `currency: str = "UYU"` to `InstallmentPurchase` (the source of truth for installment currency). |
| `models/ai_model.py:101-167` | `AIContext`: add per-currency totals alongside existing `total_gastos_mes`/`ingresos_total`. Keep `cotizacion_dolar` (line 143). |

### 2. Database Tables

| File | Change Needed |
|------|--------------|
| `database/tables.py:124` (ExpenseTable, class at 124, monto at 140) | Add `currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="UYU")` |
| `database/tables.py:84` (IncomeTable, class at 84, monto at 104) | Same `currency` column. |
| `database/tables.py:186` (InstallmentPurchaseTable) | Add `currency` column — the purchase locks currency at creation time. Generated `Expense` records inherit it via `generar_gastos_programados()` (`controllers/installment_controller.py:145`). |
| `database/tables.py:241` (InstallmentPaymentTable) | **Do NOT add `currency`.** Payments derive currency from the parent purchase via `installment_purchase_id` FK. Adding a redundant column violates the principle: only add currency where it is the source of truth. |

### 3. Migrations

**Next migration number: `015`** (latest is `014_add_password_recovery.py`).

**Migration framework is `fleting` (custom CLI), NOT Alembic.** Migrations live flat in `migrations/`, using `def up(db):` / `def down(db):` with raw SQL via `db.execute(...)`. They are tracked in the `_fleting_migrations` table. Rollback command: `fleting db rollback`. See `migrations/012_add_exchange_rates.py` for the pattern.

File: **`migrations/015_add_multi_currency.py`** (flat, not in a `versions/` subdirectory).

`up(db)` must:
1. `ALTER TABLE expenses ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'UYU'`
2. `ALTER TABLE incomes ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'UYU'`
3. `ALTER TABLE installment_purchases ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'UYU'`
4. No backfill `UPDATE` needed — PostgreSQL applies `DEFAULT 'UYU'` to existing rows atomically.

`down(db)` must:
- `ALTER TABLE expenses DROP COLUMN currency`
- `ALTER TABLE incomes DROP COLUMN currency`
- `ALTER TABLE installment_purchases DROP COLUMN currency`

**Rollback caveat (verified):** If any USD records are created after migration, rolling back **loses** that currency information (amounts survive, but the UYU/USD distinction is destroyed). This is NOT "zero data loss" once USD records exist. v1 accepts this risk; proper recovery would require re-migration.

Optional index: `CREATE INDEX idx_expenses_familia_currency ON expenses(familia_id, currency)`.

### 4. Mappers

| File | Change Needed |
|------|--------------|
| `repositories/mappers.py` | Read `row.currency` in `to_domain`; write `expense.currency` in `to_table`. **(File exists — verified.)** |
| `repositories/income_mappers.py` | Same pattern for `Income`. **(File exists — verified.)** |

### 5. Formatters (3 modules)

| File | Change Needed |
|------|--------------|
| `utils/formatters.py` | Add optional `currency: str = "UYU"` param to `format_currency` and `format_currency_with_symbol`. For `UYU` → `$ ` prefix (backward-compatible default). For `USD` → `USD ` prefix. |
| `services/infrastructure/formatters.py` | Add `currency: str = "UYU"` param to `format_pesos` and `format_pesos_ai`. Keep the function names. `format_cotizacion` stays as-is (it's for exchange rates, not amounts). |
| `services/infrastructure/formatters.py` | When `currency="USD"`, format with 2 decimals (e.g., `USD 1.250,50`) since USD amounts typically have cents. UYU stays integer-rounded. |

**Backward compatibility**: All formatters keep `currency="UYU"` as default — every existing call site works unchanged. Tests pass without rewriting. Callers only pass `currency=` when the value might be USD.

### 6. Views

| File | Change Needed |
|------|--------------|
| `views/pages/expenses_view.py` | Add currency dropdown (`UYU`/`USD`) to the form. Pass `currency` when constructing `Expense`. Display currency badge next to amount. Summary (`_render_summary`) must handle mixed-currency totals per-currency. |
| `views/pages/incomes_view.py` | Same: currency dropdown, pass `currency` to `Income`, display badge. |
| `views/pages/dashboard_view.py:84-89` | Balance calculation `ingresos - gastos` must handle mixed currencies. v1: per-currency balances. |
| `views/pages/history_view.py:74,80,160,218` | All `format_pesos(m.total_gastos)`/`format_pesos(m.total_ingresos)` calls need currency context. History shows 3 months, which may have mixed currencies. **(Verified file exists, lines confirmed.)** |
| `views/pages/planes_view.py:191,231,240` | Installment display uses `format_pesos(plan.monto_por_cuota)` and `format_pesos(plan.monto_total)` — needs currency from the `InstallmentPurchase`. **(Verified file exists, lines confirmed.)** |
| `views/components/summary_renderer.py:49,63` | `format_currency(monto)` and `f"${monto_fmt}"` — needs currency param or per-currency rendering. The renderer receives `dict[str, float]` today; must accept per-currency data. **(Verified file exists, lines confirmed.)** |
| `views/layouts/main_layout.py:220` | Exchange rate badge — already works, no change needed. |

### 7. AI Context Builders

| File | Change Needed |
|------|--------------|
| `services/ai/expense_formatters.py:36` | `agrupar_gastos()`: `total += gasto.monto` sums across currencies. Must group by `(categoria, currency)` key. |
| `services/ai/ai_advisor_service.py:157-306` | `_formatear_datos_financieros()`: All `format_pesos_ai()` calls (lines 168, 174, 176, 178, 202, 211, 222-226, 239, 248, 253, 274-302) must include currency. The method currently sums `ctx.ingresos_total - ctx.total_gastos_mes` (line 168) — this mixes currencies. |
| `services/ai/ai_advisor_service.py:308-346` | `_formatear_comparativa()`: `format_pesos_ai(m.total_actual)` etc. (lines 328-342) — currency context needed. |
| `services/ai/ai_advisor_service.py:411-424` | **System prompt MUST be revised.** Current rules: "El total mensual SIEMPRE en $ (pesos)" (line 423) and "Usá USD solo para contextualizar compras grandes" (line 424). With real USD expenses, these are incorrect. v1 requires a per-currency prompt: "Usá $ para Pesos Uruguayos. Usá USD para Dólares. Reportá cada moneda por separado. NUNCA hagas cálculos." |
| `models/ai_model.py:101-167` | `AIContext`: add per-currency fields (e.g., `gastos_por_moneda: dict[str, Decimal]`, `ingresos_por_moneda`) so `_formatear_datos_financieros` can produce per-currency lines. |

### 8. Report Service

| File | Change Needed |
|------|--------------|
| `services/infrastructure/report_service.py:131-149` | `_seccion_resumen()`: `format_pesos(ctx.ingresos_total)` — needs per-currency breakdown. **(Verified lines 131-149.)** |
| `services/infrastructure/report_service.py:153-199` | `_seccion_tabla_gastos()`: `format_pesos(monto)` per row, `total_tabla += monto` (line 180). Must group by currency. **(Verified lines 153-199.)** |

### 9. Controllers

| File | Change Needed |
|------|--------------|
| `controllers/expense_controller.py:116-121` | `get_total_by_month()` → `ExpenseService.get_total_by_month()` sums `monto` without currency filter. Must return per-currency totals or accept currency param. |
| `controllers/income_controller.py:79-84` | Same for incomes. |
| `controllers/history_controller.py:91-100` | `total_gastos = sum(g.monto ...)` and `agrupar_gastos(gastos)` — mixed-currency sum. |
| `controllers/installment_controller.py:101-171` | `generar_gastos_programados()` — line 145 creates `Expense(monto=monto_cuota, ...)` without `currency`. Must propagate `plan.currency` from `InstallmentPurchase`. |
| `controllers/exchange_rate_controller.py` | Already exists. No change needed — provides rate for future conversion functionality. |

### 10. Services (Domain)

| File | Change Needed |
|------|--------------|
| `services/domain/expense_service.py:98-101` | `get_total_by_month()` sums all expenses (line 101: `sum((expense.monto for expense in expenses), Decimal("0"))`). Add optional `currency` filter or return `dict[str, Decimal]`. **(Verified lines 98-101.)** |
| `services/domain/expense_service.py:103-117` | `get_summary_by_categories()` sums per category (line 116: `summary[categoria] += expense.monto`). Same issue. **(Verified lines 103-117.)** |
| `services/domain/income_service.py:99-102` | `get_total_by_month()` — same. |
| `services/domain/income_service.py:109-123` | `get_summary_by_categories()` — same. |

### 11. Repositories

| File | Change Needed |
|------|--------------|
| `repositories/expense_repository.py` | `get_by_month()` may need optional currency filter. No structural change — the base repo already handles generic queries. |
| `repositories/income_repository.py` | Same. |
| `repositories/base_table_repository.py` | No change needed — it's generic. |

### 12. OCR Ticket Parsing

| File | Change Needed |
|------|--------------|
| `ocr_api/main.py:40-58` | `_PROMPT_PARSEO` asks Gemma to extract `"monto"` but has no `"currency"` field in the JSON template. Add `"currency": null` to the expected JSON schema. **(Verified: the prompt at lines 40-58 expects `{"monto": 1250.0, "fecha": "...", "comercio": "...", "items": [...]}` — no currency field.)** |

**Assessment**: Gemma can potentially detect USD on receipts (receipts often show "USD", "DÓLARES", or amounts in a foreign currency context). However, Uruguayan receipts are mostly UYU. **Recommendation**: Add optional `currency` to the OCR JSON. If Gemma returns `"USD"`, use it; otherwise default to `"UYU"`. This is a soft enhancement, not a v1 blocker.

### 13. Seeds

| File | Change Needed |
|------|--------------|
| `seeds/001_gastos_ficticios.py` | All seed expenses use plain `monto` integers (UYU). Add explicit `currency="UYU"` to seed data. Optionally add 1-2 USD seed expenses to test multi-currency. |

### 14. Tests

| File | Change Needed |
|------|--------------|
| `tests/test_formatters.py` | ~30 assertions on `$ ` formatting. **Extend** (add `currency="USD"` test cases), do NOT rewrite existing UYU tests. |
| `tests/test_ai_formatters.py` | ~20 assertions on `format_pesos_ai` / `format_cotizacion`. Add USD variants. |

## Aggregation Risk (Critical)

### Where amounts are summed or compared across currencies

| Location | Code | Risk |
|----------|------|------|
| `dashboard_view.py:84` | `balance = total_ingresos - total_gastos` | **HIGH** — mixes UYU and USD if family has both |
| `expense_service.py:100-101` | `sum(expense.monto for expense in expenses)` | **HIGH** — no currency filter |
| `income_service.py:101-102` | `sum(income.monto for income in incomes)` | **HIGH** — same |
| `expense_formatters.py:36` | `resumen[cat][desc]["total"] += gasto.monto` | **HIGH** — groups by category, ignores currency |
| `history_controller.py:91-92` | `total_gastos = sum(g.monto ...)` | **HIGH** — 3-month history mixes currencies |
| `report_service.py:180` | `total_tabla += monto` | **MEDIUM** — PDF report total |
| `ai_advisor_service.py:168` | `balance_mes = ctx.ingresos_total - ctx.total_gastos_mes` | **HIGH** — AI context builds a mixed-currency balance |
| `ai_advisor_service.py:274-302` | `total_filtrado += total_categoria` | **HIGH** — AI subtotal sums across currencies |
| `planes_view.py:183` | `total_mes += plan.monto_por_cuota` | **MEDIUM** — sums per-cuota amounts from purchases |
| `installment_controller.py:138-142` | `monto_cuota = plan.monto_total - (plan.monto_por_cuota * ...)` | **LOW** — single purchase, same currency |

### Recommended Handling

**v1 approach (pragmatic):**
1. All aggregations filter or group by currency. Dashboard shows **one balance per currency** — never a single number mixing UYU and USD.
2. `get_total_by_month(year, month, currency="UYU")` — add optional currency param with default `"UYU"`.
3. `agrupar_gastos()` groups by `(categoria, currency)` and returns per-currency subtotals.
4. Dashboard balance card shows: "Balance UYU: $ X" and "Balance USD: USD Y" — no conversion.
5. Exchange rate badge remains informational only; the existing `exchange_rates` table (daily history) is available for future conversion functionality.
6. AI prompt is revised so the model never thinks it must convert or sum across currencies.

**v2 enhancement (optional, NOT in v1):**
- "Unified balance" using live or historical exchange rate from `exchange_rates`.
- Caution: the `exchange_rates` table stores daily rates. Using today's rate for old USD expenses would be historically inaccurate. To be accurate, either store the rate per transaction (v2) or use the rate from the expense date (v2).

## Approaches

### Approach A: Currency Field + Per-Currency Grouping (Recommended)

Add `currency` column to expense/income/installment_purchase tables. Formatters accept optional `currency` param. Aggregations group by currency. Dashboard shows per-currency balances.

- **Pros**: Clean, no data loss, no conversion ambiguity, backward-compatible formatters, small migration
- **Cons**: More UI work (currency dropdowns, per-currency display), slightly more complex aggregation queries
- **Effort**: Medium (touches ~22 files but changes are mechanical)

### Approach B: Separate Amount Columns (monto_uyu / monto_usd)

Add `monto_usd` column alongside `monto`. Display whichever is non-zero.

- **Pros**: No currency field needed, simple reads
- **Cons**: Wastes a column for 95% of rows (UYU-only), makes SUM queries awkward, doesn't scale to other currencies, violates normal form
- **Effort**: Medium-High

### Approach C: Store Everything in UYU, Display in USD on Demand

Keep single `monto` column (always UYU). Add a "show in USD" toggle that divides by exchange rate.

- **Pros**: Zero migration, minimal code changes
- **Cons**: Loses original USD amount (e.g., a $1,000 USD purchase at rate 40 becomes $40,000 UYU; if rate later changes to 45, displaying as USD gives $888.89 — wrong). Cannot record the actual USD price the user paid.
- **Effort**: Low but fundamentally broken for the use case

## Recommendation

**Approach A** is the correct design. The user's requirement is explicit: "record a durable good / car / imported item in USD while everyday spending stays in UYU." This means the original currency and amount must be preserved. Per-currency grouping in the dashboard avoids the conversion accuracy problem entirely.

Key design decisions for Approach A:
1. `currency` is a `String(3)` with `server_default='UYU'` — not an enum, to allow future expansion (EUR, BRL, etc.)
2. Formatters keep backward-compatible defaults — zero-risk to existing code and tests
3. Dashboard shows per-currency balances — no conversion in v1
4. AI context includes per-currency breakdown — the prompt is revised from single-currency to multi-currency
5. OCR defaults to UYU unless Gemma explicitly detects USD
6. `InstallmentPaymentTable` does NOT get a `currency` column — it derives currency from the parent purchase
7. Migration framework is `fleting` (NOT Alembic) — migrations are flat files with `up(db)`/`down(db)`

## Risks

1. **Dashboard complexity**: Showing two balances requires careful UI design. The current single-balance card is prominent; adding a second needs responsive layout work.
2. **Summary renderer**: `SummaryRenderer.render()` receives `dict[str, Decimal]` (category → amount). With mixed currencies, it needs per-currency data. Simplest v1 approach: add a `currency` param that filters before rendering.
3. **Test surface**: 100+ existing test assertions on `$ ` formatting must NOT break. Adding `currency` as an optional param with `"UYU"` default ensures this.
4. **Installment purchases**: `generar_gastos_programados()` creates `Expense` records from `InstallmentPurchase`. The purchase must carry `currency` so generated expenses inherit it.
5. **AI prompt**: The current system prompt at `ai_advisor_service.py:420-424` says "total mensual SIEMPRE en $" and "USD solo para contextualizar." This CONFLICTS with multi-currency. Must be revised.
6. **Rollback**: After USD records exist, rolling back the migration drops the `currency` column and loses that information. v1 accepts this risk.
7. **Historical data**: Existing rows get `currency='UYU'` via server default. No data migration needed, but the seed script must be updated to include the field explicitly. The `exchange_rates` table already captures daily USD/UYU rates, but v1 does not use them for transaction conversion.

## Ready for Proposal

**Yes.** The scope is well-defined, the approach is clear, and the existing exchange-rate infrastructure reduces risk. No speculative or unverified claims remain. Key corrections from the code audit:

- Migration framework is `fleting`, not Alembic.
- Migration path is flat (`migrations/015_add_multi_currency.py`), not `migrations/versions/`.
- `InstallmentPaymentTable` does not need its own `currency` column.
- AI system prompt must be revised, not just formatters.
- Rollback "zero data loss" claim is corrected: USD records would lose currency on rollback.
- All referenced files verified to exist against the real repository.
