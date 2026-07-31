# Design: Multi-Currency Support for Expenses and Incomes

## Technical Approach

Add `currency: str` (ISO 4217, `String(3)`, default `"UYU"`) to `Expense`, `Income`, and `InstallmentPurchase`. `monto` stays `Decimal`. Aggregations group or filter by `currency`; cross-currency sums are forbidden. Formatters accept optional `currency` defaulting to `"UYU"` (zero-risk backward compat). Migration is `fleting` 015, additive, no backfill.

Sequence: 1) migration → 2) tables → 3) Pydantic models + validator → 4) mappers → 5) formatters (3 modules) → 6) `SummaryRenderer` Decimal sig → 7) services return `dict[str, Decimal]` → 8) controllers → 9) views (dropdowns, badges, dual cards) → 10) `AIContext` per-currency + prompt revision → 11) `agrupar_gastos` group by `(categoria, currency)` → 12) OCR optional currency → 13) seeds + tests. Steps 1-6 extend the schema and models with `currency VARCHAR(3) DEFAULT 'UYU'` but keep functional behavior unchanged: all amounts remain UYU, formatters produce identical output, and no multi-currency logic is active. The schema IS changed (new column), but user-visible behavior is unchanged. Steps 7+ surface per-currency math.

## Architecture Decisions

| # | Decision | Chosen vs rejected | Why |
|---|----------|--------------------|-----|
| 1 | USD format precision | **MUST 2 decimals** vs integer rounding | USD amounts routinely have cents; rounding drops real money. |
| 2 | `AIContext` shape | **`dict[str, Decimal]` per side** vs flat `gastos_uyu/usd` | Canonical spec; future-proof for EUR/BRL without schema churn. |
| 3 | `SummaryRenderer` strategy | **filter param + Decimal sig** vs full per-currency dict | Smaller blast radius; one call site at a time becomes per-currency. |
| 4 | Rounding policy | UYU `quantize("1", HALF_UP)`; USD `quantize("0.01", HALF_UP)`; storage/sums exact | Spec currency end-to-end invariant. |
| 5 | `format_currency` float compat | **Decimal-only contract; `float` accepted internally during migration** vs public `float \| Decimal` | Public interface MUST be `Decimal` per end-to-end invariant. Existing `test_formatters.py` `float` assertions will be migrated to `Decimal` in task 4.2. During the migration window, the formatter internally converts `float` via `Decimal(str(v))` to keep old tests green, but this is an implementation detail — the documented contract is `Decimal` only. |

## Data Flow (USD expense)

```
ExpensesView (currency dropdown)
  └─► Expense(monto=Decimal("1250.50"), currency="USD")
  └─► ExpenseController → Service (Pydantic validator) → Repository
        └─► mapper (row.currency="USD", row.monto=Decimal("1250.50"))
              → expenses.currency VARCHAR(3), expenses.monto Numeric(12,2)
Dashboard:
  ExpenseService.get_total_by_month → {"UYU": 4500, "USD": 1250.50}
  IncomeService.get_total_by_month  → {"UYU": 20000, "USD": 0}
  balance_uyu = 15500; balance_usd = -1250.50
  Two cards: "$ 15.500" and "USD 1.250,50"
AI: AIContext.gastos_por_moneda / ingresos_por_moneda;
  prompt: "Balance UYU $ 15500 / Balance USD 1250.50 (negativo)".
  Gemma NUNCA hace cálculos.
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `migrations/015_add_multi_currency.py` | Create | `up`: 3× `ALTER TABLE … ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'UYU'`; optional `idx_expenses_familia_currency`. `down`: 3× `DROP COLUMN currency`. |
| `database/tables.py` | Modify | Add `currency` on `IncomeTable` (84), `ExpenseTable` (124), `InstallmentPurchaseTable` (186). **Not** on `InstallmentPaymentTable`. |
| `models/{expense,income,installment}_model.py` | Modify | Add `currency: str = "UYU"` + `field_validator` allowing `{"UYU","USD"}`. |
| `models/ai_model.py` | Modify | Add `gastos_por_moneda`, `ingresos_por_moneda: dict[str, Decimal]` to `AIContext`. |
| `repositories/mappers.py`, `income_mappers.py` | Modify | Read/write `row.currency` ↔ domain. |
| `utils/formatters.py`, `services/infrastructure/formatters.py` | Modify | `format_currency`, `format_currency_with_symbol`, `format_pesos`, `format_pesos_ai` accept `currency="UYU"`. UYU=`$ N`; USD=`USD N.NN`. |
| `views/components/summary_renderer.py` | Modify | `summary: dict[str, float]` → `dict[str, Decimal]`; new `currency` param. |
| `services/domain/{expense,income}_service.py` | Modify | Return `dict[str, Decimal]`; accept `currency` filter. |
| `controllers/{expense,income,history}_controller.py` | Modify | Thread `currency`; return per-currency dicts. |
| `controllers/installment_controller.py:145` | Modify | `Expense(... currency=plan.currency)` in `generar_gastos_programados`. |
| `views/pages/{expenses,incomes}_view.py` | Modify | Currency `ft.Dropdown` (UYU/USD). Pass to domain. Badge in list. |
| `views/pages/dashboard_view.py` | Modify | Two balance cards in `ft.ResponsiveRow` (UYU/USD), fed per-currency. |
| `views/pages/history_view.py`, `planes_view.py` | Modify | Per-currency totals. `planes_view.py:181-183` sum per-currency. |
| `services/ai/expense_formatters.py:36` | Modify | `agrupar_gastos` keys on `(categoria, desc, currency)`. |
| `services/ai/ai_advisor_service.py` | Modify | `_formatear_datos_financieros` iterates per-currency dicts; `_formatear_comparativa` per-currency lines. |
| `services/ai/ai_advisor_service.py:420-424` | Modify | Remove "total mensual SIEMPRE en $"; add "Reportá cada moneda por separado. NUNCA conviertas ni sumes monedas distintas." Keep "NUNCA hacer cálculos". |
| `services/infrastructure/report_service.py` | Modify | Per-currency breakdown; `total_tabla` reset per currency. |
| `ocr_api/main.py:40-58,550-571`, `ocr_api/models.py:48` | Modify | Add `"currency": "UYU"` to prompt JSON; `currency: str\|None` on `OCRResponse`; treat `None`/unsupported as `"UYU"`. |
| `seeds/001_gastos_ficticios.py` | Modify | Add `currency` key; include 1-2 USD examples. |
| `tests/test_formatters.py`, `tests/test_ai_formatters.py` | Modify | Add USD cases; UYU assertions untouched. |

## Interfaces / Contracts

```python
PerCurrencyTotals = dict[str, Decimal]   # keys: "UYU" | "USD"

class ExpenseService:
    def get_total_by_month(self, year: int, month: int,
                           currency: str | None = None) -> PerCurrencyTotals: ...
    def get_summary_by_categories(
        self, year: int | None, month: int | None, currency: str | None = None,
    ) -> dict[tuple[str, str], Decimal]: ...

def format_currency(value: Decimal, currency: str = "UYU") -> str
def format_pesos(monto: Decimal, currency: str = "UYU") -> str       # "$ 1.250" / "USD 1.250,50"
def format_pesos_ai(monto: Decimal, currency: str = "UYU") -> str    # "$ 1250" / "USD 1250.50"

# Note: format_currency internally converts float via Decimal(str(v)) during the
# migration window (task 4.2 migrates existing float callers). The public contract
# is Decimal-only, per the Decimal end-to-end invariant.

class SummaryRenderer:
    @staticmethod
    def render(summary: dict[str, Decimal], color: str, color_bg: str,
               currency: str = "UYU",
               empty_msg: str = "No hay registros") -> ft.Column: ...
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Pydantic: `EUR` rejected, `USD` accepted | Extend `test_expense_model.py`. |
| Unit | `format_currency(Decimal("1250.50"), "USD") == "USD 1.250,50"` | Extend `test_formatters.py`. |
| Unit | `agrupar_gastos([g_uyu, g_usd])` keeps currency separate | New in `test_ai_formatters.py`. |
| Unit | `format_pesos` USD 2dp; UYU integer | Extend `test_ai_formatters.py`. |
| Integration | `up` adds 3 columns w/ default; `down` drops them | `fleting db migrate` + `rollback` in test DB. |
| Integration | `get_total_by_month` returns `{"UYU": …, "USD": …}` for mixed seed | Extend `test_expense_service.py`. |
| Integration | `generar_gastos_programados` copies `plan.currency` | New `test_installment_controller.py`. |
| AI RED | Prompt no longer contains "total mensual SIEMPRE en $"; contains "NUNCA conviertas" | `test_ai_prompt.py` substring assertions. |
| E2E | Dashboard renders two cards; stacks on mobile | Manual + ResponsiveRow assertions. |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary is touched. The change is domain logic + UI + DB schema.

## Migration / Rollout

`fleting` migration 015 additive: 3× `ALTER TABLE … ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'UYU'`. PostgreSQL applies the constant default atomically; no backfill `UPDATE`, no table rewrite. Each `ALTER` is its own statement so a failure leaves no partial state. `down(db)` drops the three columns. Optional index `idx_expenses_familia_currency (familia_id, currency)` for tenant-scoped per-currency queries. **Rollback caveat** (already in proposal): if USD rows exist when rolling back, currency distinction is destroyed; amounts survive. v1 accepts this; recovery requires re-migration with backfill.

## Open Questions

None. The five pending decisions are resolved in the Architecture Decisions table above.
