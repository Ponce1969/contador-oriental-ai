# Per-Currency Aggregation Specification

## Purpose
Specifies that all monetary aggregation MUST group or filter by currency, enforcing the cross-currency-operation invariant (Invariant 1) across the dashboard, history, reports, AI context, and installment totals.

## ADDED Requirements

### Requirement: Aggregations group or filter by currency
Every code path that sums, subtracts, or compares monetary amounts — including `ExpenseService.get_total_by_month`, `get_summary_by_categories`, `IncomeService` equivalents, `agrupar_gastos()`, `history_controller` monthly totals, `report_service._seccion_tabla_gastos`, dashboard balance, and AI context builders — MUST either group results by `currency` or pre-filter to a single `currency`. No code path SHALL produce a scalar total mixing currencies.

#### Scenario: Same-currency aggregation works
- GIVEN UYU expenses `1000` and `2000`
- WHEN a total is computed
- THEN `UYU 3000` is returned

#### Scenario: Mixed-currency aggregation prevents a combined scalar
- GIVEN UYU expenses `1000` and USD expenses `100`
- WHEN a combined total is requested without an explicit currency filter
- THEN the system MUST NOT return a single number combining both currencies
- AND the result MUST be per-currency (e.g. `{"UYU": 1000, "USD": 100}`)

### Requirement: agrupar_gastos groups by category and currency
`agrupar_gastos()` MUST group running totals by `(categoria, currency)`. The category subtotal accumulator MUST NOT sum `monto` across currencies. The previous behavior at `services/ai/expense_formatters.py:36` where `total += gasto.monto` summed across currencies MUST be removed.

#### Scenario: Same category, different currencies stay separate
- GIVEN two transport expenses: UYU 1000 and USD 50
- WHEN `agrupar_gastos()` runs
- THEN the transport category MUST contain two distinct subtotals, one per currency
- AND neither subtotal combines UYU and USD

### Requirement: History per-currency totals
`history_controller` monthly totals MUST be computed per currency. The 3-month history display MUST show per-currency totals and MUST NOT sum UYU and USD into one monthly figure.

#### Scenario: Mixed-currency month in history
- GIVEN a history month has UYU gastos 5000 and USD gastos 200
- WHEN that month is rendered
- THEN the month MUST display UYU and USD gastos separately
- AND a combined monthly gastos figure SHALL NOT appear

### Requirement: Report service per-currency sections
`report_service._seccion_resumen` and `_seccion_tabla_gastos` MUST produce per-currency totals. The PDF/table running total `total_tabla += monto` MUST accumulate within a single currency only.

#### Scenario: Report table grouping
- GIVEN a report month has mixed-currency rows
- WHEN the table section is rendered
- THEN rows MUST be grouped or ordered so the running total stays within a single currency
- AND a grand total mixing currencies MUST NOT appear

### Requirement: SummaryRenderer per-currency support
`SummaryRenderer` MUST support per-currency rendering, either by accepting a `currency` filter parameter or by accepting per-currency dict data. The existing `dict[str, float]` signature MUST be updated to `dict[str, Decimal]` — `float` SHALL NOT represent monetary values (see currency spec Decimal end-to-end invariant). The UYU rendering path with `$ ` prefix and integer rounding MUST remain backward-compatible when only UYU data is provided.

#### Scenario: Render USD summary
- GIVEN `SummaryRenderer` is given USD-category amounts
- WHEN it renders
- THEN figures MUST be `USD `-prefixed (2 decimals)
- AND UYU amounts MUST NOT be mixed into the same summary block