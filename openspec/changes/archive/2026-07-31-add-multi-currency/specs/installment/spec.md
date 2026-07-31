# Installment Currency Specification

## Purpose
Defines that `InstallmentPurchase` carries currency as the source of truth, generated expenses inherit it, and `installment_payments` does NOT carry its own currency column.

## ADDED Requirements

### Requirement: InstallmentPurchase carries currency
`InstallmentPurchase` MUST include a `currency: str = "UYU"` field with a Pydantic field validator that restricts values to `UYU` and `USD`. A purchase locks its currency at creation time; `monto_total` and `monto_por_cuota` are denominated in that currency. (Currency validation rules are defined in the currency spec.)

#### Scenario: USD installment purchase
- GIVEN a user creates a purchase in USD with `monto_total=2000`
- WHEN persisted
- THEN `InstallmentPurchase.currency` MUST equal `"USD"`
- AND `monto_total` represents USD 2000

#### Scenario: UYU default purchase
- GIVEN a user creates a purchase without selecting currency
- WHEN persisted
- THEN `currency` MUST equal `"UYU"`

### Requirement: Generated expenses inherit purchase currency
`generar_gastos_programados()` MUST copy `plan.currency` onto each generated `Expense`. Generated expenses MUST NOT default to `"UYU"` when the purchase is in USD (current behavior at `controllers/installment_controller.py:145` MUST be corrected).

#### Scenario: USD purchase generates USD expenses
- GIVEN a USD purchase with 10 installments
- WHEN `generar_gastos_programados()` runs
- THEN every generated `Expense` MUST have `currency == "USD"`
- AND each `Expense.monto` MUST equal `monto_por_cuota` in USD

#### Scenario: UYU purchase generates UYU expenses
- GIVEN a UYU purchase with installments
- WHEN `generar_gastos_programados()` runs
- THEN every generated `Expense` MUST have `currency == "UYU"`

### Requirement: InstallmentPayments derive currency via FK
`InstallmentPayment` MUST NOT have its own `currency` column. A payment's currency is the currency of its parent `InstallmentPurchase` via `installment_purchase_id`.

#### Scenario: Payment currency resolution
- GIVEN a USD purchase has a recorded payment
- WHEN the payment's currency is needed
- THEN the system MUST resolve it from the parent purchase's `currency`
- AND no `currency` column SHALL be added to the `installment_payments` table

### Requirement: Planes view shows currency
`planes_view` MUST display the currency of each plan alongside `monto_por_cuota` and `monto_total` (lines 191, 231, 240). Monthly totals of per-cuota amounts MUST be computed per currency and MUST NOT sum UYU and USD together (current behavior at `planes_view.py:183` MUST be corrected).

#### Scenario: Planes per-currency monthly total
- GIVEN the month has UYU purchases and USD purchases
- WHEN `planes_view` sums per-cuota amounts for the month
- THEN the totals MUST be split by currency
- AND UYU and USD per-cuota amounts MUST NOT be summed together

#### Scenario: Plan row currency badge
- GIVEN a USD purchase is displayed in `planes_view`
- WHEN the plan row renders
- THEN `monto_por_cuota` and `monto_total` MUST be `USD `-prefixed