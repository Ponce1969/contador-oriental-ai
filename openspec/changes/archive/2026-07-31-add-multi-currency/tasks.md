# Tasks: Multi-Currency Support for Expenses and Incomes

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~530 (authored) |
| 400-line budget risk | **High** |
| Chained PRs recommended | **Yes** |
| Suggested split | PR1→PR2→PR3→PR4 |
| Delivery strategy | `ask-on-risk` |
| Chain strategy | **stacked-to-main** |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

> Threat matrix: N/A per design (no routing, shell, subprocess, VCS, exec-file boundary).

### Work Units

| Unit | PR | Test | Harness | Rollback |
|------|----|------|---------|----------|
| 1 Schema+models+mappers+formatters+Renderer | PR1 | `pytest tests/test_formatters.py tests/test_expense_model.py tests/test_income_model.py tests/test_installment_model.py` | `fleting db migrate`+`rollback` | revert before USD rows = zero data loss |
| 2 Services+controllers+views per-currency | PR2 | `pytest tests/test_expense_service.py tests/test_income_service.py tests/test_installment_controller.py` | UYU+USD expenses; 2 cards | revert keeps PR1, layers default to UYU |
| 3 AIContext+prompt+agrupar_gastos+OCR | PR3 | `pytest tests/test_ai_formatters.py tests/test_ai_prompt.py tests/test_ai_advisor_service.py` | chat + OCR USD hint | AI+report+ocr_api revert; data on disk intact |
| 4 USD seeds + extended tests | PR4 | `uv run pytest -v` | `fleting db seed`; UI smoke | seeds+tests only; no prod code touched |

## Phase 1: Foundation

- [x] 1.1 `migrations/015_add_multi_currency.py`: 3× `ALTER TABLE … ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'UYU'` (expenses, incomes, installment_purchases) + optional `idx_expenses_familia_currency`; `down` drops 3 columns.
- [x] 1.2 `database/tables.py`: add `currency String(3)` to `ExpenseTable`/`IncomeTable`/`InstallmentPurchaseTable`. NOT `InstallmentPaymentTable`.
- [x] 1.3 `models/expense_model.py`: `currency: str = "UYU"` + `@field_validator` `{"UYU","USD"}`; update `monto` description + `__str__`.
- [x] 1.4 `models/income_model.py`: same.
- [x] 1.5 `models/installment_model.py`: same for `InstallmentPurchase` only.
- [x] 1.6 `models/ai_model.py`: add `gastos_por_moneda`, `ingresos_por_moneda: dict[str, Decimal]` to `AIContext`; keep `cotizacion_dolar`.
- [x] 1.7 `repositories/mappers.py`: read/write `row.currency` for `Expense`.
- [x] 1.8 `repositories/income_mappers.py`: same for `Income`.
- [x] 1.9 `utils/formatters.py`: `currency: str = "UYU"` on `format_currency`+`format_currency_with_symbol`; UYU=`$ `, USD=`USD `; public contract `Decimal`-only (float accepted internally via `Decimal(str(v))` during migration; float callers migrated in 4.2).
- [x] 1.10 `services/infrastructure/formatters.py`: `currency` on `format_pesos` (UYU `quantize("1", HALF_UP)`; USD `quantize("0.01", HALF_UP)`) + `format_pesos_ai`. Leave `format_cotizacion`.
- [x] 1.11 `views/components/summary_renderer.py`: `summary: dict[str, float]` → `dict[str, Decimal]`; add `currency: str = "UYU"` filter.

## Phase 2: Services+Controllers+Views

- [x] 2.1 `services/domain/expense_service.py`: `get_total_by_month`+`get_summary_by_categories` return `PerCurrencyTotals = dict[str, Decimal]`; accept `currency: str | None = None`.
- [x] 2.2 `services/domain/income_service.py`: mirror.
- [x] 2.3 `controllers/expense_controller.py`: thread `currency`; consume per-currency dict.
- [x] 2.4 `controllers/income_controller.py`: mirror.
- [x] 2.5 `controllers/history_controller.py`: per-currency totals (3-month window may mix).
- [x] 2.6 `controllers/installment_controller.py:145`: pass `currency=plan.currency` to generated `Expense`.
- [x] 2.7 `views/pages/expenses_view.py`: `ft.Dropdown` UYU/USD, pass to `Expense`, render badge.
- [x] 2.8 `views/pages/incomes_view.py`: same.
- [x] 2.9 `views/pages/dashboard_view.py`: replace single card with 2 cards in `ft.ResponsiveRow` (UYU+USD).
- [x] 2.10 `views/pages/history_view.py`: per-currency `format_pesos` + totals.
- [x] 2.11 `views/pages/planes_view.py`: per-currency per-cuota totals + row badge.

## Phase 3: AI+OCR

- [x] 3.1 `services/ai/expense_formatters.py:36`: `agrupar_gastos` key becomes `(categoria, desc, currency)`.
- [x] 3.2 `services/ai/ai_advisor_service.py` `_formatear_datos_financieros`: iterate `gastos_por_moneda`/`ingresos_por_moneda`; replace mixed `balance_mes` (L168) with per-currency balances.
- [x] 3.3 `services/ai/ai_advisor_service.py` `_formatear_comparativa`: each `total_actual` line carries currency.
- [x] 3.4 RED `tests/test_ai_prompt.py`: assert L420-424 lacks "total mensual SIEMPRE en $" + "USD solo para contextualizar", contains "NUNCA conviertas" + "Reportá cada moneda por separado". Confirm RED.
- [x] 3.5 GREEN revise `ai_advisor_service.py:420-424`: remove the two rules, add per-currency guidance; keep "NUNCA hacer cálculos". Confirm GREEN.
- [x] 3.6 `services/infrastructure/report_service.py`: per-currency sections; reset `total_tabla` per currency.
- [x] 3.7 `ocr_api/main.py:40-58` `_PROMPT_PARSEO`: add `"currency": null` to expected JSON.
- [x] 3.8 `ocr_api/models.py:48`: add `currency: str | None = None` to `OCRResponse`; `ocr_api/main.py:550-571` treats `None`/unsupported as `"UYU"` without altering `monto`.

## Phase 4: Seeds + Tests

- [x] 4.1 `seeds/001_gastos_ficticios.py`: `currency="UYU"` on all seeds; add 1-2 USD examples.
- [x] 4.2 `tests/test_formatters.py`: USD cases (e.g. `format_pesos(Decimal("1250.50"), "USD") == "USD 1.250,50"`). UYU untouched.
- [x] 4.3 `tests/test_ai_formatters.py`: USD cases for `agrupar_gastos` + `format_pesos` (2dp USD / integer UYU).
- [x] 4.4 `tests/test_expense_model.py`+`tests/test_income_model.py`: `EUR` rejected, `USD` accepted, `UYU` default.
- [x] 4.5 `tests/test_installment_controller.py`: USD purchase → all generated `Expense` carry `currency="USD"`.
- [x] 4.6 Guard: `uv run pytest -v` green; `uv run ruff check .`+`uv run ty check .` clean; `fleting db seed` + UI smoke.

## Phase 5: Cleanup

- [x] 5.1 `README.md`+`AGENTS.md`: document multi-currency, dual dashboard cards, USD rollback caveat.
- [x] 5.2 Final `uv run ruff format .`+`uv run ty check .`; remove temp debug.
