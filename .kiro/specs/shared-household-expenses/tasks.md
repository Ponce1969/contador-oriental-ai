# Implementation Plan: Shared Household Expenses

## Overview

Additive feature that introduces a cross-family Household entity on top of the existing multi-tenant
model. No existing tables change shape. Implementation follows the established MVC + Services +
Repositories layering. Tasks are ordered by dependency: migrations → models/errors → repositories
→ services → controller → UI → events/AI → tests → docs.

## Tasks

- [ ] 1. Database migrations

  - [ ] 1.1 Create migration `017_add_household_tables.py`
    - Create tables: `hogares`, `household_members`, `household_invitations`,
      `shared_expense_links`, `household_settlements`, `household_audit_log`
    - Add all FK constraints, unique constraints, and indexes as specified in design
    - Implement `up()` and `down()` functions following the pattern in `migrations/016_update_exchange_rates.py`
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 7.1, 10.5_

  - [ ] 1.2 Create migration `018_add_household_id_to_ai_vector_memory.py`
    - Add nullable `household_id INTEGER REFERENCES hogares(id) ON DELETE CASCADE`
    - Add partial index `idx_ai_vector_memory_household ON ai_vector_memory(household_id) WHERE household_id IS NOT NULL`
    - Implement `up()` and `down()` following the same migration pattern
    - _Requirements: 9.1, 9.4_

- [ ] 2. Custom errors and domain models

  - [ ] 2.1 Add household custom errors to `models/errors.py`
    - Add frozen dataclasses: `NotFoundError`, `UnauthorizedError`, `HouseholdConflictError`,
      `AdminMustTransferError`, `BalanceNotZeroError`, `NotAMemberError`, `InvalidInvitationError`,
      `InvitationLimitError`, `DuplicateLinkError` — all extending `AppError`
    - _Requirements: 1.4, 1.6, 2.2, 2.4, 2.5, 3.2, 3.4, 4.2, 4.3, 4.4, 4.6_

  - [ ] 2.2 Create `models/household_model.py` with all Pydantic domain models
    - Implement frozen Pydantic models: `Household`, `HouseholdMember`, `HouseholdInvitation`,
      `HouseholdJoinResult`, `SharedExpenseLink`, `SharedExpenseFeedItem`, `MemberBalance`,
      `HouseholdSettlement`, `ExpenseFeedPage`
    - All monetary fields use `Decimal`; no `float` anywhere
    - _Requirements: 1.1, 2.1, 4.1, 5.2, 6.1, 7.1_

- [ ] 3. SQLAlchemy table definitions

  - [ ] 3.1 Add household SQLAlchemy table classes to `database/tables.py`
    - Add: `HogarTable`, `HouseholdMemberTable`, `HouseholdInvitationTable`,
      `SharedExpenseLinkTable`, `HouseholdSettlementTable`, `HouseholdAuditLogTable`
    - Add `household_id` nullable column to existing `AIVectorMemoryTable`
    - Match column types, FK `ondelete` behaviors, and index definitions from design exactly
    - _Requirements: 1.1, 9.4_

- [ ] 4. Repository layer — `repositories/household/`

  - [ ] 4.1 Create `repositories/household/__init__.py` and `HouseholdRepository`
    - Implement: `create()`, `get_by_id()`, `set_disbanded()`
    - _Requirements: 1.1, 3.3_

  - [ ] 4.2 Create `HouseholdMemberRepository` in `repositories/household/member_repository.py`
    - Implement: `get_active_membership()`, `get_members()`, `add_member()`,
      `remove_member()`, `is_active_member()`, `get_member_role()`
    - _Requirements: 1.3, 2.3, 3.1, 3.2, 3.4, 6.1_

  - [ ] 4.3 Create `HouseholdInvitationRepository` in `repositories/household/invitation_repository.py`
    - Implement: `create()`, `get_by_token()`, `count_active()`, `mark_accepted()`, `mark_revoked()`
    - `count_active()` only counts rows with `status='pending'` and `expires_at > now()`
    - _Requirements: 2.1, 2.2, 2.3, 2.6_

  - [ ] 4.4 Create `SharedExpenseLinkRepository` in `repositories/household/link_repository.py`
    - Implement: `create()`, `get_by_gasto_and_household()`, `delete_by_gasto_and_household()`,
      `delete_all_for_member()`, `delete_all_for_household()`, `get_feed()`,
      `sum_contributions_per_member()`
    - `get_feed()` returns `(list[SharedExpenseFeedItem], int)` with inner join on `gastos` + `familias`
    - _Requirements: 4.1, 4.5, 5.1, 5.2, 5.3, 5.4, 6.1_

  - [ ] 4.5 Create `HouseholdSettlementRepository` in `repositories/household/settlement_repository.py`
    - Implement: `create()`, `sum_per_member()` returning `{familia_id: {paid: Decimal, received: Decimal}}`
    - _Requirements: 6.4, 7.1_

  - [ ] 4.6 Create `HouseholdAuditLogRepository` in `repositories/household/audit_repository.py`
    - Implement: `append()` — called at the repository layer on every link creation/deletion
    - _Requirements: 10.5_

  - [ ] 4.7 Add household memory methods to `repositories/memoria_repository.py`
    - Add: `guardar_con_household()`, `eliminar_household_vector()`, `buscar_similares_por_household()`
    - `guardar_con_household()` inserts with `household_id` set; `eliminar_household_vector()`
      matches on `source_type='shared_expense'`, `source_id`, and `household_id` only
    - _Requirements: 9.1, 9.4, 9.5_

- [ ] 5. Service layer — `services/domain/household/`

  - [ ] 5.1 Create `HouseholdService` in `services/domain/household/household_service.py`
    - Implement `create_household()` with check order: membership conflict → name validation → DB write
    - Implement `leave_household()` with atomic non-admin path (delete member + links) and
      admin-only disband path (set disbanded + delete all members + links); must enforce `BalanceNotZeroError`
    - Implement `transfer_admin()`
    - Implement `get_household_for_familia()`
    - _Requirements: 1.1–1.6, 3.1–3.5_

  - [ ] 5.2 Create `InvitationService` in `services/domain/household/invitation_service.py`
    - Implement `create_invitation()`: verify admin role → check count < 10 → generate token (secrets.token_urlsafe(32)) → set expires_at = now + 48h
    - Implement `accept_invitation()`: token validity → membership conflict → atomic accept + add member
    - Implement `revoke_invitation()`: verify admin role → verify pending status → mark revoked
    - _Requirements: 2.1–2.7_

  - [ ] 5.3 Create `ExpenseSharingService` in `services/domain/household/expense_sharing_service.py`
    - Implement `create_link()` with strict check order: caller membership → expense exists →
      ownership authz (before duplicate) → duplicate check → insert link + audit log
    - Implement `delete_link()`: caller membership → link exists → delete + audit log
    - Implement `create_expense_and_link()`: atomic INSERT gastos + INSERT shared_expense_links;
      rollback both on any failure
    - _Requirements: 4.1–4.8_

  - [ ] 5.4 Create `HouseholdBalanceService` in `services/domain/household/balance_service.py`
    - Implement `compute_balance()`: validate date order → verify caller membership →
      fetch members → sum contributions → sum settlements → compute equal_share (Decimal division) →
      compute net_balance per member; zero-sum invariant enforced by construction
    - `Decimal("0")` as all accumulators; no `float` at any step
    - _Requirements: 6.1–6.7_

  - [ ] 5.5 Create `SettlementService` in `services/domain/household/settlement_service.py`
    - Implement `record_settlement()` with check order: authz (caller == payer) → self-settlement →
      monto > 0 → both parties active members → create record → fire_and_forget(SETTLEMENT_CREADO)
    - _Requirements: 7.1–7.6_

  - [ ] 5.6 Create `services/domain/household/__init__.py`
    - Export all five service classes for clean imports
    - _Requirements: all household requirements_

- [ ] 6. Checkpoint — core domain complete
  - Ensure `uv run ruff check .` passes and `uv run ty check .` has no new errors.
  - Ask the user if any service interface needs adjustment before building the controller.

- [ ] 7. Controller layer

  - [ ] 7.1 Create `controllers/household_controller.py` — `HouseholdController`
    - Inherit `BaseController`; use `_get_session()` context manager pattern
    - Implement all methods from design interface: household lifecycle (including `transfer_admin`), invitations,
      expense sharing, feed, balance, settlements
    - Each method wires the correct repos + service + passes `self._familia_id`
    - `record_settlement()` passes `authenticated_familia_id=self._familia_id` to service
    - `share_expense()` fires `SHARED_EXPENSE_LINK_CREADO`; `unshare_expense()` fires
      `SHARED_EXPENSE_LINK_ELIMINADO` via injected `event_system`
    - _Requirements: 1.1–10.5_

- [ ] 8. Event system additions

  - [ ] 8.1 Add new `EventType` values to `core/events.py`
    - Add: `SHARED_EXPENSE_LINK_CREADO`, `SHARED_EXPENSE_LINK_ELIMINADO`, `SETTLEMENT_CREADO`
    - _Requirements: 9.4, 9.5, 7.6_

  - [ ] 8.2 Create `services/ai/household_memory_handler.py`
    - Implement `handle_shared_expense_link_creado()`: vectorize shared expense text with
      `household_id` tag using `MemoriaRepository.guardar_con_household()`
    - Implement `handle_shared_expense_link_eliminado()`: delete household-scoped vector via
      `MemoriaRepository.eliminar_household_vector()`; leave family-scoped vector untouched
    - _Requirements: 9.2, 9.4, 9.5_

  - [ ] 8.3 Register event handlers in `core/app.py`
    - Subscribe `handle_shared_expense_link_creado` to `SHARED_EXPENSE_LINK_CREADO`
    - Subscribe `handle_shared_expense_link_eliminado` to `SHARED_EXPENSE_LINK_ELIMINADO`
    - _Requirements: 9.4, 9.5_

- [ ] 9. UI — route registration and navigation

  - [ ] 9.1 Add household routes to `configs/routes.py`
    - Add three routes: `/hogar`, `/hogar/crear`, `/hogar/unirse`
    - Set `show_in_top: False` and `show_in_bottom: False` on all three (conditional rendering in layout)
    - _Requirements: 8.1, 8.2_

  - [ ] 9.2 Update `views/layouts/main_layout.py` for conditional Hogar nav entry
    - At layout construction, call `HouseholdController.get_current_household()`
    - If result is `Ok(Household)` → render `🏠 Hogar` nav item pointing to `/hogar`
    - If result is `Ok(None)` → render `🏠 Crear hogar compartido` pointing to `/hogar/crear`
    - _Requirements: 8.1, 8.2_

- [ ] 10. UI — Household views

  - [ ] 10.1 Create `views/pages/household_create_view.py` — `HouseholdCreateView`
    - Form with household name `ft.TextField` + confirm `ft.Button`
    - On success redirect to `/hogar`; inline error display for `ValidationError` / `HouseholdConflictError`
    - _Requirements: 1.1–1.6, 8.1_

  - [ ] 10.2 Create `views/pages/household_join_view.py` — `HouseholdJoinView`
    - Token input `ft.TextField` + join `ft.Button`
    - On success redirect to `/hogar`; inline errors for `InvalidInvitationError` / `HouseholdConflictError`
    - _Requirements: 2.3–2.5, 8.1_

  - [ ] 10.3 Create `views/pages/household_view.py` — `HouseholdView` skeleton with `ft.Tabs`
    - Three tabs using `ft.Tabs(tab_alignment=ft.TabAlignment.FILL)`: Gastos | Balance | Miembros
    - Store `_cached_feed: list[SharedExpenseFeedItem] = []` at construction (empty-state guarantee)
    - `UnauthorizedError` renders access-denied message with no data widgets
    - _Requirements: 8.3, 8.6, 10.3_

  - [ ] 10.4 Implement Gastos tab content in `HouseholdView`
    - On load: render from `_cached_feed` immediately (empty-state message if empty), then refresh from `get_expense_feed()`
    - Date range filter row + optional familia filter dropdown
    - Pagination controls; each item shows family chip, description, amount, category, date
    - Optimistic update callback: prepend new item via `_append_shared_expense()` before server confirmation
    - _Requirements: 5.1–5.7, 8.3, 8.4_

  - [ ] 10.5 Implement Balance tab content in `HouseholdView`
    - On tab select: call `get_balance()` (always fresh)
    - Per-member card: family name, contributed, equal share, signed net balance (`+$X` / `-$X`)
    - Period selector (date range) to filter balance computation
    - _Requirements: 6.1–6.7, 8.5_

  - [ ] 10.6 Implement Miembros tab content in `HouseholdView`
    - List all active members with role badges
    - Admin: show invitation token as copyable text with `ft.IconButton` copy action (no `page.launch_url()`)
    - Admin: show `Transferir Admin` action next to other members to transfer admin role
    - Per-member row: if `net_balance != 0`, show `💸 Registrar pago` button opening settlement dialog
    - Settlement form dialog: amount `ft.TextField` (Decimal), date picker, confirm
    - `Abandonar hogar` button at bottom with confirmation dialog
    - _Requirements: 8.3, 8.5, 8.7_

- [ ] 11. Checkpoint — full vertical slice working
  - Run `uv run ruff check .` and `uv run ty check .`; fix any issues before proceeding to tests.
  - Ask the user to verify UI navigation flow manually if possible.

- [ ] 12. Unit tests

  - [ ] 12.1 Create `tests/test_household_service.py`
    - Test `create_household()`: success, conflict error before name validation (Property 2), name trimming
    - Test `leave_household()`: non-admin path atomicity, admin-with-members returns `AdminMustTransferError`,
      last-admin disband path, not-a-member returns `NotAMemberError`, settlements preserved, non-zero balance rejected
    - Test `transfer_admin()`: success, not-an-admin, target-not-a-member
    - _Requirements: 1.1–1.6, 3.1–3.5_

  - [ ] 12.2 Create `tests/test_invitation_service.py`
    - Test `create_invitation()`: success, non-admin rejected, limit at 10, accepted/revoked do not count
    - Test `accept_invitation()`: success, expired token, accepted token, revoked token, conflict on double-join
    - Test `revoke_invitation()`: success, already-accepted returns `InvalidInvitationError`
    - _Requirements: 2.1–2.7_

  - [ ] 12.3 Create `tests/test_expense_sharing_service.py`
    - Test `create_link()` check ordering: UnauthorizedError before DuplicateLinkError (Property 8),
      NotFoundError, NotAMemberError
    - Test `delete_link()`: success, not-found error, gasto row unchanged after delete (Property 9)
    - Test `create_expense_and_link()`: success, rollback when link insert fails
    - _Requirements: 4.1–4.8_

  - [ ] 12.4 Create `tests/test_household_balance_service.py`
    - Test Decimal-only arithmetic with no float contamination
    - Test zero-sum with zero expenses returns `Decimal("0.00")` per member
    - Test period filter excludes out-of-range expenses, ValidationError on inverted range
    - Test settlements are included in balance (payer balance increases, recipient decreases)
    - _Requirements: 6.1–6.7_

  - [ ] 12.5 Create `tests/test_settlement_service.py`
    - Test check ordering: UnauthorizedError, self-settlement ValidationError, non-positive monto,
      non-member NotAMemberError
    - Test successful settlement emits `SETTLEMENT_CREADO` event
    - _Requirements: 7.1–7.6_

  - [ ] 12.6 Create `tests/test_household_repository.py`
    - Test `get_feed()` inner-join isolation (expense without link not returned — Property 21)
    - Test feed ordering by `fecha` descending (Property 11)
    - Test pagination: `total_count` stable, all items across pages (Property 13)
    - Test `count_active()` excludes accepted/revoked/expired invitations (Property 5)
    - _Requirements: 5.1–5.7, 10.1, 10.2_

  - [ ] 12.7 Create `tests/test_household_audit_log.py`
    - Test every `create_link()` writes exactly one audit entry with `action="created"`
    - Test every `delete_link()` writes exactly one audit entry with `action="deleted"`
    - Test no extra audit entries created on error paths
    - _Requirements: 10.5_

- [ ] 13. Property-based tests (hypothesis)

  - [ ] 13.1 Create `tests/test_household_properties.py` — scaffolding and shared strategies
    - Add `hypothesis` to `pyproject.toml` dev dependencies (`hypothesis>=6.100`)
    - Add `--hypothesis-seed=0` to `[tool.pytest.ini_options]` in `pyproject.toml`
    - Write shared `st.strategies` helpers: `household_name_strategy`, `monto_strategy`,
      `member_count_strategy`, `date_strategy`
    - _Requirements: all_

  - [ ] 13.2 Write property test for Property 1 — single active household membership
    - `# Feature: shared-household-expenses, Property 1`
    - `@given` familia already in a household → `create_household()` and `accept_invitation()` both return `HouseholdConflictError`
    - Verify no new records created
    - _Requirements: 1.3, 1.4, 2.5_

  - [ ]* 13.3 Write property test for Property 2 — conflict check precedes name validation
    - `# Feature: shared-household-expenses, Property 2`
    - `@given` already-member familia + invalid name → result is `HouseholdConflictError`, not `ValidationError`
    - _Requirements: 1.4_

  - [ ]* 13.4 Write property test for Property 3 — name trimming and length enforcement
    - `# Feature: shared-household-expenses, Property 3`
    - `@given` names of random whitespace-padded strings and lengths → stored name equals `name.strip()`;
      empty/whitespace/>100-char trimmed names return `ValidationError`
    - _Requirements: 1.5, 1.6_

  - [ ]* 13.5 Write property test for Property 4 — token uniqueness and single-use
    - `# Feature: shared-household-expenses, Property 4`
    - `@given` N in [2, 20] → create N invitations → all tokens pairwise distinct
    - Accept valid token → second accept attempt returns `InvalidInvitationError`
    - _Requirements: 2.1, 2.3_

  - [ ]* 13.6 Write property test for Property 5 — active invitation limit
    - `# Feature: shared-household-expenses, Property 5`
    - `@given` mix of accepted/revoked/pending invitations → 11th pending invite returns `InvitationLimitError`;
      accepted/revoked do not count toward limit
    - _Requirements: 2.2_

  - [ ]* 13.7 Write property test for Property 6 — invalid token states return InvalidInvitationError
    - `# Feature: shared-household-expenses, Property 6`
    - `@given` token status ∈ {accepted, revoked, expired} → `accept_invitation()` returns `InvalidInvitationError`
    - No new `household_members` row created
    - _Requirements: 2.4_

  - [ ]* 13.8 Write property test for Property 7 — non-admin leave atomicity
    - `# Feature: shared-household-expenses, Property 7`
    - `@given` N ∈ [0, 10] shared expenses → after `leave_household()`: zero member rows, zero link rows,
      all original `gastos` rows intact, all `household_settlements` rows intact
    - _Requirements: 3.1, 3.5_

  - [ ]* 13.9 Write property test for Property 8 — authz check precedes duplicate check
    - `# Feature: shared-household-expenses, Property 8`
    - `@given` existing link for (gasto_id, household_id) → different familia_id (non-owner) attempt
      returns `UnauthorizedError`, not `DuplicateLinkError`
    - _Requirements: 4.3, 10.4_

  - [ ]* 13.10 Write property test for Property 9 — shared link round-trip / gasto immutability
    - `# Feature: shared-household-expenses, Property 9`
    - `@given` valid triple → create link → all gasto fields identical; delete link → gasto still identical
    - Link count is exactly 1 after create, 0 after delete
    - _Requirements: 4.1, 4.5_

  - [ ]* 13.11 Write property test for Property 10 — idempotent duplicate detection
    - `# Feature: shared-household-expenses, Property 10`
    - `@given` existing link → second `create_link()` by same owner returns `DuplicateLinkError`;
      link count remains exactly 1
    - _Requirements: 4.4_

  - [ ]* 13.12 Write property test for Property 11 — feed ordered by fecha descending
    - `# Feature: shared-household-expenses, Property 11`
    - `@given` list of dates (not all identical) → `get_expense_feed()` result is sorted descending;
      total count equals N
    - _Requirements: 5.1, 5.2_

  - [ ]* 13.13 Write property test for Property 12 — date range filter is inclusive and exclusive
    - `# Feature: shared-household-expenses, Property 12`
    - `@given` start_date, end_date, list of expense dates → every returned item satisfies
      `start_date <= fecha <= end_date`; no out-of-range item appears
    - _Requirements: 5.3_

  - [ ]* 13.14 Write property test for Property 13 — pagination correctness
    - `# Feature: shared-household-expenses, Property 13`
    - `@given` N expenses, page_size ∈ [1, 100] → `total_count` is N on every page;
      union of all pages contains each item exactly once in consistent order
    - _Requirements: 5.4_

  - [ ]* 13.15 Write property test for Property 14 — inverted date range returns ValidationError
    - `# Feature: shared-household-expenses, Property 14`
    - `@given` start_date > end_date → both `get_expense_feed()` and `compute_balance()` return
      `ValidationError` without reading any DB rows
    - _Requirements: 5.7, 6.7_

  - [ ]* 13.16 Write property test for Property 15 — balance zero-sum invariant
    - `# Feature: shared-household-expenses, Property 15`
    - `@given` expenses (Decimal list), n_members ∈ [2, 5] → `sum(net_balance) == Decimal("0.00")`
    - No `float` object may appear in any intermediate computation (inspect via `hypothesis.extra`)
    - `@settings(max_examples=100)`
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [ ]* 13.17 Write property test for Property 16 — settlement shifts payer and recipient by exact monto
    - `# Feature: shared-household-expenses, Property 16`
    - `@given` pre-settlement balances, monto > 0 → after settlement: payer net_balance increases by
      exactly monto, recipient net_balance decreases by exactly monto; zero-sum still holds
    - _Requirements: 6.4, 7.1_

  - [ ]* 13.18 Write property test for Property 17 — settlement authz
    - `# Feature: shared-household-expenses, Property 17`
    - `@given` authenticated_familia_id ≠ payer_familia_id → `record_settlement()` returns `UnauthorizedError`;
      no `household_settlements` row created
    - _Requirements: 7.2_

  - [ ]* 13.19 Write property test for Property 18 — self-settlement always rejected
    - `# Feature: shared-household-expenses, Property 18`
    - `@given` any familia_id, any valid monto, any household → `payer == recipient` always returns
      `ValidationError` regardless of membership or amount
    - _Requirements: 7.4_

  - [ ]* 13.20 Write property test for Property 19 — non-positive settlement amount rejected
    - `# Feature: shared-household-expenses, Property 19`
    - `@given` monto ≤ Decimal("0") (including zero, negative) → `record_settlement()` returns `ValidationError`
    - _Requirements: 7.5_

  - [ ]* 13.21 Write property test for Property 20 — audit log completeness
    - `# Feature: shared-household-expenses, Property 20`
    - `@given` sequence of create/delete link calls → audit log contains exactly one entry per call
      with correct `action`, `familia_id`, `gasto_id`, `household_id`; error paths produce zero entries
    - _Requirements: 10.5_

  - [ ]* 13.22 Write property test for Property 21 — feed isolation via inner join
    - `# Feature: shared-household-expenses, Property 21`
    - `@given` gastos belonging to member familia with no `shared_expense_link` →
      those gastos never appear in `get_expense_feed()` for any filter combination
    - _Requirements: 10.1, 10.2_

- [ ] 14. Integration tests

  - [ ]* 14.1 Create `tests/test_household_atomic_operations.py`
    - Test `leave_household()` (non-admin): simulate DB failure after member delete → both member
      and links rolled back; original gastos rows intact
    - Test `create_expense_and_link()`: simulate failure after INSERT gastos → both rows rolled back
    - Test admin disband: simulate failure after `set_disbanded()` → all changes rolled back
    - _Requirements: 3.1, 3.3, 4.7_

  - [ ]* 14.2 Create `tests/test_household_ai_context.py`
    - Mock `EmbeddingService`; test that `SHARED_EXPENSE_LINK_CREADO` event triggers vector insert
      with correct `household_id` and text including `familia_nombre`
    - Test `SHARED_EXPENSE_LINK_ELIMINADO` deletes household-scoped vector but leaves family-scoped
      vector unchanged
    - Test `buscar_similares_por_household()` returns only records tagged with the target `household_id`
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 15. Final checkpoint — all tests passing
  - Run `uv run pytest -v tests/test_household_*.py`
  - Run `uv run ruff check .` and `uv run ruff format .`
  - Ensure all tests pass; ask the user if questions arise.

- [ ] 16. Documentation updates

  - [ ] 16.1 Update `AGENTS.md` to reference the new spec files
    - Add row for `shared-household-expenses` spec in the Specification Files table
    - _Requirements: all_

  - [ ] 16.2 Update `tests/COBERTURA_TESTS.md` with household test coverage summary
    - List new test files, number of unit/PBT/integration tests, and which requirements they cover
    - _Requirements: all_

