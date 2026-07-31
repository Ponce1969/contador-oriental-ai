# Currency Specification

## Purpose
Defines the `currency` attribute carried by monetary records, the two architectural invariants that govern all monetary operations, and currency formatting rules. This is the foundational domain referenced by every other domain in this change.

## ADDED Requirements

### Requirement: Currency attribute representation
The system MUST represent currency as a 3-character ISO 4217 code string (`String(3)`) and MUST NOT use an enum. v1 MUST support `UYU` and `USD`; additional codes (EUR, BRL) MAY be added later without schema migration.

#### Scenario: Valid currency codes
- GIVEN a monetary record is created
- WHEN `currency` is `"UYU"` or `"USD"`
- THEN the record MUST be persisted with that exact code
- AND queries filtering by `currency` MUST match it

#### Scenario: Unknown currency extensibility
- GIVEN a future change adds `"EUR"`
- WHEN a record is created with `currency="EUR"`
- THEN no schema migration SHALL be REQUIRED to store it

### Requirement: Currency representation — ISO code for logic, symbol for display
The `currency` field MUST store an ISO 4217 currency code (`"UYU"`, `"USD"`) and MUST NOT store display symbols (`$`, `USD`, `U$S`, `$U`). Presentation is a separate concern: the formatters translate ISO codes to display symbols at the UI boundary. This separation is mandatory:
- **Persistence and logic**: `currency = "UYU"` or `currency = "USD"` (ISO 4217 codes).
- **Display**: UYU is shown as `$`, USD is shown as `USD`. Never use `$` or any symbol as the value of the `currency` field.

#### Scenario: Currency field stores ISO code, not symbol
- GIVEN an expense is created with `currency = "UYU"` and `monto = Decimal("1250.50")`
- WHEN persisted and displayed
- THEN the database column MUST contain `"UYU"` (not `"$"`)
- AND the UI MUST render `$ 1.250,50` (the formatter translates `"UYU"` → `$ `)
- AND the formatter MUST NOT accept `"$"` as a valid currency value

#### Scenario: USD stored as ISO code, displayed as label
- GIVEN an expense with `currency = "USD"` and `monto = Decimal("1250.50")`
- WHEN displayed
- THEN the UI MUST render `USD 1.250,50`
- AND the currency field value at every internal boundary MUST remain `"USD"`, never `"US$"`, `"$U"`, or `"$"`

### Requirement: Single-currency amount preservation
The system MUST preserve the original `monto` Decimal value alongside its `currency`. The system MUST NOT silently convert an amount from one currency to another in v1.

#### Scenario: Original amount preserved
- GIVEN a user records an expense of `USD 1250.50`
- WHEN the record is loaded later
- THEN `monto` MUST equal `Decimal("1250.50")` and `currency` MUST equal `"USD"`
- AND no conversion to UYU SHALL have been applied

### Requirement: Cross-currency operations are forbidden (Invariant 1)
The system MUST NOT add, subtract, or compare monetary amounts of different currencies without an explicit conversion step and a defined exchange-rate policy. Conversion is out of scope for v1. Therefore any aggregation of mixed currencies MUST be prevented by grouping or filtering on `currency`. This invariant applies to dashboard balance, expense/income summaries, history, reports, AI context, and `agrupar_gastos()`.

#### Scenario: Same-currency sum permitted
- GIVEN expenses `UYU 1000` and `UYU 500`
- WHEN a total is computed
- THEN the result MUST be `UYU 1500`

#### Scenario: Mixed-currency sum prohibited
- GIVEN expenses `UYU 1000` and `USD 100`
- WHEN a single combined total is requested without an explicit currency filter
- THEN the system MUST refuse to return a single scalar total
- AND the operation MUST either raise an error or return per-currency totals grouped by `currency`

### Requirement: Balances are computed per currency (Invariant 2)
The system MUST compute balances per currency as `balance_<ccy> = ingresos_<ccy> - gastos_<ccy>`. The system MUST NOT expose a single "balance" that mixes UYU and USD. This applies to the dashboard, AI context, and report service.

#### Scenario: Per-currency balances
- GIVEN a family has UYU incomes 20000, UYU expenses 12000, USD incomes 1000, USD expenses 400
- WHEN the balance is computed
- THEN `balance_UYU` MUST be `UYU 8000` and `balance_USD` MUST be `USD 600`
- AND no combined "balance" scalar mixing currencies SHALL be produced

### Requirement: Backward-compatible currency-aware formatters
The formatters `format_currency`, `format_currency_with_symbol`, `format_pesos`, and `format_pesos_ai` MUST accept an optional `currency: str = "UYU"` parameter. UYU output MUST remain the existing peso-prefixed, integer-rounded output. USD output SHOULD use 2 decimals with an `USD ` prefix.

#### Scenario: UYU default unchanged
- GIVEN `format_pesos(Decimal("1500"))` is called with no currency argument
- THEN output MUST equal the pre-change peso output
- AND existing formatter tests MUST pass unmodified

#### Scenario: USD formatting with cents
- GIVEN `format_pesos(Decimal("1250.50"), currency="USD")` is called
- THEN output MUST use an `USD ` prefix and 2 decimals
- AND UYU integer rounding MUST NOT be applied to USD amounts

### Requirement: v2 conversion is separate explicit decision
The system MUST NOT provide automatic currency conversion in v1. Any future `UYU + USD -> UYU equivalent` via `ExchangeRateService` is a separate domain decision and MUST NOT appear implicitly in the dashboard or reports. The existing `exchange_rates` table (daily USD/UYU rates) is available but MUST NOT be used for transaction conversion in v1.

#### Scenario: No implicit conversion
- GIVEN a family has UYU and USD records
- WHEN the dashboard renders
- THEN no exchange-rate conversion SHALL be applied to combine balances
- AND the exchange-rate badge MAY remain informational only

### Requirement: Currency code validation at domain boundary
The domain model MUST validate that `currency` is one of the supported codes (`UYU`, `USD`) before persistence. This validation SHALL be enforced via a Pydantic field validator on `Expense` and `Income` domain models. Extension to new currency codes requires updating this validation list — the `String(3)` column type alone provides schema extensibility, not runtime validation.

#### Scenario: Supported code passes
- GIVEN `currency = "USD"` is assigned to an Expense
- WHEN the Pydantic validator runs
- THEN the value MUST be accepted

#### Scenario: Unsupported code rejected
- GIVEN `currency = "EUR"` is assigned to an Expense
- WHEN the Pydantic validator runs
- THEN validation MUST fail
- AND the expense MUST NOT be persisted

### Requirement: Canonical per-currency totals representation
All per-currency monetary totals SHALL use a single canonical representation across every layer: `dict[str, Decimal]` where keys are currency codes and values are Decimal amounts. Services, controllers, views, AIContext, and report service MUST use this same shape. No layer SHALL introduce its own ad-hoc structure (tuple, named tuple, list of pairs, or separate per-currency fields that duplicate the dict semantics).

#### Scenario: Service returns canonical shape
- GIVEN `get_total_by_month()` produces per-currency totals
- WHEN results are returned
- THEN the return type MUST be `dict[str, Decimal]` (e.g. `{"UYU": Decimal("5000"), "USD": Decimal("200")}`)

#### Scenario: AIContext uses canonical shape
- GIVEN `AIContext` stores per-currency totals
- WHEN `gastos_por_moneda` or `ingresos_por_moneda` is populated
- THEN the field type MUST be `dict[str, Decimal]`

### Requirement: Decimal end-to-end for all monetary values
All monetary amounts MUST use `Decimal` in every architectural layer. `float` SHALL NOT represent money. The following rules are mandatory:
- Domain models (`Expense.monto`, `Income.monto`, `InstallmentPurchase.monto_total`) MUST use `Decimal`.
- SQLAlchemy columns MUST use `Numeric` (maps to `Decimal`), NEVER `Float`.
- Services and controllers MUST perform all arithmetic with `Decimal`; `sum(Decimal("0"), ...)` pattern.
- Formatters MUST accept `Decimal` and return `str`; they MAY accept `float` for backward compatibility but MUST convert internally to `Decimal`.
- AIContext monetary fields MUST be `Decimal`.
- OCR-parsed amounts MUST be converted directly to `Decimal` without passing through `float`.
- `SummaryRenderer` MUST accept monetary values as `Decimal`, not `float`.
- Conversions `Decimal → float` and `float → Decimal` are forbidden for monetary values. Rounding policy MUST be explicit via `Decimal.quantize()`.

#### Scenario: No float in money path
- GIVEN any monetary value flowing through the system
- WHEN it passes between layers
- THEN its type MUST be `Decimal` at every boundary
- AND a `float` representation SHALL NOT appear in any money-carrying field, parameter, or return value

#### Scenario: OCR amount straight to Decimal
- GIVEN OCR parses `monto = 1250.50` from a ticket
- WHEN the value is stored
- THEN `monto` MUST be `Decimal("1250.50")`
- AND no intermediate `float` SHALL be used