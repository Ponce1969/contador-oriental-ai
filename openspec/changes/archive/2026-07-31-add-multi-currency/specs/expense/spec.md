# Expense Specification

## Purpose
Defines how an `Expense` carries its currency, how expenses are created and persisted, and how expense totals respect the cross-currency invariant.

## ADDED Requirements

### Requirement: Expense carries currency
The `Expense` domain model MUST include a `currency: str = "UYU"` field with a Pydantic field validator that restricts values to `UYU` and `USD`. `monto` MUST remain `Decimal`. The pair `(monto, currency)` is the source of truth for the money value. (Currency validation rules are defined in the currency spec.)

#### Scenario: Expense created in UYU
- GIVEN the user creates an expense of `1500` in the expenses form
- WHEN no currency is selected
- THEN the persisted `Expense` MUST have `currency == "UYU"`
- AND `monto == Decimal("1500")`

#### Scenario: Expense created in USD
- GIVEN the user selects `USD` and enters `1250.50`
- WHEN the expense is saved
- THEN the persisted `Expense` MUST have `currency == "USD"` and `monto == Decimal("1250.50")`

### Requirement: Expense form currency selector
The expenses form MUST present a currency selector offering at least `UYU` and `USD`. The selected currency MUST be passed when constructing the `Expense`. A currency badge MUST be displayed beside the amount in the expenses list.

#### Scenario: Currency badge shown
- GIVEN a USD expense in the list
- WHEN the list renders
- THEN the row MUST display an `USD ` currency prefix or badge
- AND a UYU row MUST display the `$ ` peso prefix

### Requirement: Expense mappers carry currency
The expense mapper MUST read `row.currency` into the domain model and write `expense.currency` into the table row. The mapper MUST preserve `"UYU"` as the default for legacy rows.

#### Scenario: Mapper round-trip of USD expense
- GIVEN a USD expense is persisted
- WHEN it is loaded back through the mapper
- THEN the domain `Expense.currency` MUST equal `"USD"`

### Requirement: Expense totals per currency
`ExpenseService.get_total_by_month` and `get_summary_by_categories` MUST return per-currency totals (e.g., `dict[str, Decimal]`) or accept an explicit `currency` filter parameter. They MUST NOT sum `monto` across currencies.

#### Scenario: Per-currency monthly totals
- GIVEN a month has UYU expenses summing 5000 and USD expenses summing 200
- WHEN totals are requested
- THEN `get_total_by_month` MUST return per-currency totals such as `{"UYU": 5000, "USD": 200}`
- AND no scalar combined total SHALL be produced

#### Scenario: Category summary grouped by currency
- GIVEN the month has UYU transport 1000 and USD transport 50
- WHEN `get_summary_by_categories` runs
- THEN the result MUST keep UYU and USD transport totals separate, keyed by `(categoria, currency)`

### Requirement: Multi-tenant currency filtering
All expense queries MUST continue to filter by `familia_id`. The currency filter MUST compose with the tenant filter; currency MUST NOT replace tenant isolation.

#### Scenario: Currency filter respects tenant boundary
- GIVEN family A has a USD expense and family B has a USD expense
- WHEN family A requests USD totals
- THEN only family A's USD expense is included
- AND family B's records MUST NOT leak