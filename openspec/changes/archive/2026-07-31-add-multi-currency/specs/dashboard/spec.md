# Dashboard Specification

## Purpose
Defines the per-currency dashboard balance cards and the prohibition of a single mixed-currency balance (Invariant 2).

## ADDED Requirements

### Requirement: Per-currency balance cards
The dashboard MUST display two independent balance cards: one for UYU and one for USD. Each card shows `balance_<ccy> = ingresos_<ccy> - gastos_<ccy>`. The dashboard MUST NOT compute or display a single balance that mixes currencies.

#### Scenario: Both currencies present
- GIVEN UYU balance is 8000 and USD balance is 600
- WHEN the dashboard renders
- THEN a "Balance UYU" card and a "Balance USD" card MUST both render
- AND no combined balance value SHALL appear

#### Scenario: Only one currency present
- GIVEN a family has only UYU records
- WHEN the dashboard renders
- THEN a UYU balance card MUST render
- AND the USD card MAY render as `USD 0,00` or be omitted

### Requirement: Responsive dual-card layout
The two balance cards SHOULD render side-by-side on wide screens and stack vertically on narrow screens. The layout MUST NOT break on mobile-width viewports.

#### Scenario: Narrow viewport stacking
- GIVEN a mobile-width viewport
- WHEN the dashboard renders the two cards
- THEN the cards MUST stack vertically without horizontal clipping

### Requirement: Currency badge on every dashboard figure
Every monetary figure on the dashboard MUST be currency-prefixed or carry a currency badge, so the currency of each number is unambiguous.

#### Scenario: Ambiguous figures avoided
- GIVEN a dashboard summary line shows a UYU total
- THEN the line MUST use the `$ ` peso prefix
- AND a USD total line MUST use the `USD ` prefix

### Requirement: Dashboard uses per-currency service outputs
The dashboard MUST source balances from per-currency income and expense totals. It MUST NOT fall back to a single-currency `ingresos_total - total_gastos` expression when both currencies exist.

#### Scenario: Mixed-currency family never combined
- GIVEN a family has UYU and USD records in the current month
- WHEN the dashboard balance runs
- THEN the computation MUST call per-currency service methods
- AND the legacy single-currency balance expression MUST NOT be used for mixed-currency cases