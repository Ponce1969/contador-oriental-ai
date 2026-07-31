# Income Specification

## Purpose
Defines how an `Income` carries its currency, how incomes are created and persisted, and how income totals respect the cross-currency invariant.

## ADDED Requirements

### Requirement: Income carries currency
The `Income` domain model MUST include a `currency: str = "UYU"` field with a Pydantic field validator that restricts values to `UYU` and `USD`. `monto` MUST remain `Decimal`. (Currency validation rules are defined in the currency spec.)

#### Scenario: Income created in USD
- GIVEN the user selects `USD` and enters a salary of `2000`
- WHEN the income is saved
- THEN the persisted `Income` MUST have `currency == "USD"` and `monto == Decimal("2000")`

#### Scenario: Income UYU default
- GIVEN a legacy or seed income with no currency specified
- WHEN loaded
- THEN `currency` MUST default to `"UYU"`

### Requirement: Income form currency selector
The incomes form MUST present a currency selector offering at least `UYU` and `USD`. The selected currency MUST be passed when constructing the `Income`. A currency badge MUST be displayed beside the amount in the incomes list.

#### Scenario: Selector drives field
- GIVEN the user selects `USD` in the incomes form
- WHEN the income is constructed and saved
- THEN the persisted `Income.currency` MUST equal `"USD"`

### Requirement: Income mappers carry currency
The income mapper MUST read and write `currency`. Legacy rows derive `"UYU"` from the column server default.

#### Scenario: Mapper round-trip
- GIVEN a USD income persisted
- WHEN reloaded via the mapper
- THEN the domain `Income.currency` MUST equal `"USD"`

### Requirement: Income totals per currency
`IncomeService.get_total_by_month` and `get_summary_by_categories` MUST return per-currency totals or accept an explicit `currency` filter parameter. They MUST NOT sum `monto` across currencies.

#### Scenario: Per-currency income totals
- GIVEN a month has UYU incomes 30000 and USD incomes 1500
- WHEN totals are requested
- THEN the result MUST be per-currency, e.g. `{"UYU": 30000, "USD": 1500}`
- AND no combined scalar total SHALL be produced

### Requirement: Per-currency income feeds dashboard balance
Income totals fed to the dashboard balance MUST be per currency, enabling `balance_<ccy> = ingresos_<ccy> - gastos_<ccy>` (Invariant 2). A single mixed-currency income total MUST NOT feed the balance computation.

#### Scenario: Mixed currencies not combined for balance
- GIVEN UYU incomes and USD incomes both exist
- WHEN the dashboard computes balances
- THEN each currency's income total is computed independently and paired with that currency's expense total