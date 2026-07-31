# Archive Report: Multi-Currency Support (USD + UYU)

**Change**: `add-multi-currency`
**Archived**: 2026-07-31
**Status**: Complete ✅

## Summary
Added USD as an alternative currency alongside Uruguayan peso (UYU) for expenses and incomes. Users can now record purchases in their original currency. v1 shows per-currency balances (no conversion). The existing exchange-rate infrastructure (daily USD/UYU rates) remains available for future conversion functionality.

## Artifacts
| Artifact | Status |
|----------|--------|
| `exploration.md` | ✅ ~22 affected files mapped; Approach A selected |
| `proposal.md` | ✅ 7 business rules, scope in/out, rollback plan |
| `specs/` (9 domains) | ✅ 48 requirements, 66 Given/When/Then scenarios |
| `design.md` | ✅ 13-step sequence, 5 architecture decisions, all contracts |
| `tasks.md` | ✅ 38 tasks, all `[x]` |
| `verify-report.md` | ✅ Approved — 92 tests, zero blockers |

## Implementation (4 stacked PRs)
| PR | Scope | Tests |
|----|-------|-------|
| PR1 | Migration 015, tables, models, mappers, formatters, SummaryRenderer | 44 ✅ |
| PR2 | Services per-currency, controllers, 5 views (dropdowns, dual cards) | 18 ✅ |
| PR3 | AI context, prompt revision, agrupar_gastos, report service, OCR | 20 ✅ |
| PR4 | USD seeds, extended tests, docs, final guard | 108 total ✅ |

## Key Decisions
- `currency`: `String(3)` ISO 4217 codes (UYU/USD), NOT an enum. Extensible to EUR/BRL.
- Display: `$` for UYU, `USD` for USD. Never U$S or $U.
- v1: per-currency balances, no conversion. `ExchangeRateService` unused for transactions.
- Decimal end-to-end: no `float` for money in any layer.
- `InstallmentPaymentTable` does NOT get `currency` column (derives from purchase via FK).
- AI prompt revised: removed "total mensual SIEMPRE en $" and "USD solo para contextualizar."

## Known Issues
- sdd-attempt ledger CLI bug (GitHub issue #2107) — ledger not used for this change
- 2 pre-existing test fixture gaps (WARNING, not blockers)
- Rollback after USD records loses currency info (documented, accepted v1 risk)

## Files Changed
40+ files across all layers: migrations, database, models, mappers, formatters, services, controllers, views, AI, OCR, seeds, tests, docs.
