# AI Context Specification

## Purpose
Defines how AI context carries per-currency totals and how the AI system prompt is revised to forbid cross-currency calculation.

## ADDED Requirements

### Requirement: AIContext carries per-currency totals
`AIContext` MUST include per-currency totals (`gastos_por_moneda: dict[str, Decimal]` and `ingresos_por_moneda: dict[str, Decimal]`) alongside existing fields. All monetary values in `AIContext` MUST be `Decimal` — see currency spec Decimal end-to-end invariant. The model MUST receive pre-calculated per-currency figures and MUST NOT receive only a single mixed-currency `total_gastos_mes` as the sole monetary total.

#### Scenario: Per-currency totals present
- GIVEN UYU gastos 5000 and USD gastos 200
- WHEN `AIContext` is built
- THEN `gastos_por_moneda` MUST contain `{"UYU": 5000, "USD": 200}`
- AND a mixed-currency single `total_gastos` SHALL NOT be the only figure exposed to the model

### Requirement: AI advisor never calculates across currencies
`_formatear_datos_financieros` MUST NOT compute `balance_mes = ctx.ingresos_total - ctx.total_gastos_mes` as a single mixed-currency figure (the current behavior at `ai_advisor_service.py:168`). It MUST format per-currency balances. The AI model MUST NOT be asked to perform financial calculations.

#### Scenario: Per-currency balance in prompt
- GIVEN UYU balance 8000 and USD balance 600
- WHEN the AI advisor formats finances
- THEN the prompt MUST present `Balance UYU` and `Balance USD` as separate lines
- AND no combined balance line SHALL be emitted

### Requirement: System prompt revised for multi-currency
The system prompt at `ai_advisor_service.py:420-424` MUST be revised to remove the rules "El total mensual SIEMPRE en $" and "Usá USD solo para contextualizar." The revised prompt MUST instruct per-currency reporting and MUST retain the "NUNCA hacer cálculos" rule.

#### Scenario: Old prompt rules removed
- GIVEN the revised system prompt
- WHEN inspected
- THEN it MUST NOT contain "total mensual SIEMPRE en $"
- AND it MUST NOT instruct that USD is only for context

#### Scenario: Per-currency guidance present
- GIVEN the revised system prompt
- WHEN inspected
- THEN it MUST instruct the model to report each currency separately using `$` for UYU and `USD` for USD
- AND it MUST instruct the model not to convert or sum across currencies

### Requirement: Comparativa formatting is per-currency
`_formatear_comparativa` MUST format each `total_actual` and subtotal with its currency. Cross-currency comparisons MUST NOT be summed into a single series.

#### Scenario: Comparativa spans currencies
- GIVEN the comparativa contains UYU and USD monthly totals
- WHEN formatted
- THEN each line MUST be currency-prefixed
- AND the section MUST NOT show a combined series

### Requirement: Per-currency formatting in AI builders
Every `format_pesos_ai()` call inside `_formatear_datos_financieros` and `_formatear_comparativa` MUST include the appropriate currency argument. UYU and USD figures MUST be rendered with their distinct prefixes.

#### Scenario: USD line in AI context
- GIVEN an AI context line for a USD total of 600
- WHEN formatted via `format_pesos_ai`
- THEN the line MUST use the `USD ` prefix with 2 decimals