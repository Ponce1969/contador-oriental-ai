# OCR Currency Detection Specification

## Purpose
Defines how the OCR ticket parser extracts an optional currency and falls back to UYU. USD detection is a soft enhancement and MUST NOT block the expense-creation flow.

## ADDED Requirements

### Requirement: OCR JSON includes optional currency
The OCR prompt schema at `ocr_api/main.py:40-58` MUST include an optional `"currency"` field in the parsed ticket JSON. When the model cannot confidently detect currency, the parser MUST default to `"UYU"`.

#### Scenario: USD detected
- GIVEN a ticket that clearly shows USD
- WHEN Gemma parses it
- THEN the returned JSON MUST contain `"currency": "USD"`
- AND the created expense MUST carry `currency="USD"`

#### Scenario: Ambiguous currency defaults to UYU
- GIVEN a ticket where currency is ambiguous
- WHEN the parsed JSON omits or nulls `currency`
- THEN the system MUST default to `"UYU"`
- AND a created expense MUST carry `currency="UYU"`

### Requirement: OCR currency is a soft enhancement
USD detection MUST NOT block the expense-creation flow. If detection is unavailable, parsing MUST still succeed with `currency="UYU"`.

#### Scenario: Detection field missing
- GIVEN the OCR service returns no `currency` field
- WHEN the calling code treats the absence as `"UYU"`
- THEN the expense is created with `currency="UYU"`
- AND no parse error SHALL be raised solely due to a missing `currency` field

### Requirement: Only UYU and USD accepted in v1
If the OCR model returns a currency code other than `UYU` or `USD`, the system MUST treat the currency detection as invalid/ambiguous and default `currency` to `"UYU"` (identical behavior to when no currency is detected at all). The `monto` value MUST NOT be altered, converted, or reinterpreted in any way. Storing a non-UYU ticket as UYU due to ambiguous detection is an accepted OCR limitation for v1 — it is NOT a currency conversion. The system SHALL NOT silently store an unsupported currency code.

#### Scenario: Unsupported code from OCR treated as ambiguous
- GIVEN OCR returns `"currency": "EUR"` with `"monto": 500`
- WHEN the expense is created
- THEN `currency` MUST be `"UYU"` (the detection is ignored, same as ambiguous)
- AND `monto` MUST be `Decimal("500")` — NOT converted, NOT reinterpreted
- AND `"EUR"` MUST NOT be persisted to the database

### Requirement: OCR-created expense carries detected currency
An expense created from an OCR result MUST persist the resolved `currency` alongside the detected `monto`. The OCR-provided amount and currency MUST NOT be coerced into a different currency without an explicit conversion policy (none in v1).

#### Scenario: OCR USD amount preserved
- GIVEN OCR returns `monto=1250.50` and `currency="USD"`
- WHEN the expense is persisted
- THEN `monto == Decimal("1250.50")` and `currency == "USD"`
- AND no conversion to UYU SHALL occur