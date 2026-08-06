# Requirements Document

## Introduction

This feature enables two or more users of Contador Oriental — each with their own family account (`familia_id`) — to form a **Shared Household** and collaboratively track expenses. Each member continues logging private expenses under their own family, but they can additionally mark individual expenses as shared, see a consolidated household view, and track who owes what to balance costs.

The key design decision is that a Shared Household is a **new, independent entity** — not an extension of an existing family — so that neither family's data isolation is compromised and no existing multi-tenant invariant needs to change.

---

## Glossary

- **Family**: An existing `familias` record. Each family retains its own isolated data.
- **Household**: A new entity (`hogares` table) that groups two or more families for shared expense tracking. A family may belong to at most one active Household at a time.
- **Household_Member**: A join record linking a Family to a Household, carrying a role (`admin` or `member`).
- **Shared_Expense**: An existing `gastos` record that has been linked to a Household via the `shared_expense_links` table, making it visible in the Household view.
- **Household_Balance**: A computed snapshot showing each member's net position (total contributed minus equal share owed).
- **Settlement**: A directional payment record (`household_settlements`) between two members that reduces the outstanding balance.
- **Invitation**: A token-based request sent from one Family to another to join the Household.
- **Household_Admin**: The Household_Member with the `admin` role. The first member to create the Household becomes the admin. There is always at least one admin.
- **Household_AI_Context**: The scope of data visible to the AI Advisor when a user queries from within the Household view — includes all shared expenses from all members.

---

## Requirements

### Requirement 1: Create a Shared Household

**User Story:** As a family account owner, I want to create a Shared Household and invite other families to join, so that we can start tracking expenses together.

#### Acceptance Criteria

1. WHEN a Family submits a create-Household request with a display name and their `familia_id`, THE Household_Manager SHALL create a new Household record containing a unique identifier, the trimmed display name, and the creator's `familia_id` as the first Household_Admin, and return the new Household identifier.
2. WHEN a Household is created, THE Household_Manager SHALL assign the creating family the `admin` role and set the Household status to `active`.
3. THE Household_Manager SHALL enforce that a Family may belong to at most one active Household at a time.
4. IF a Family is already a member of an active Household and requests to create or join another Household, THEN THE Household_Manager SHALL return a `HouseholdConflictError` without creating or modifying any record; this membership check SHALL be performed before any display name validation.
5. THE Household_Manager SHALL require a Household display name that, after whitespace trimming, is between 1 and 100 characters in length.
6. IF a submitted display name is empty, contains only whitespace, or exceeds 100 characters after trimming, THEN THE Household_Manager SHALL return a `ValidationError` without creating any record.

---

### Requirement 2: Invite and Join a Household

**User Story:** As a Household Admin, I want to invite other family accounts to my Household, so that they can participate in shared expense tracking.

#### Acceptance Criteria

1. WHEN a Household_Admin requests to invite a Family, THE Invitation_Manager SHALL generate a unique, single-use invitation token associated with the Household and store it with an expiry timestamp of 48 hours from creation.
2. THE Invitation_Manager SHALL enforce that at most 10 active (non-expired, non-accepted, non-revoked) invitations exist per Household at any given time; IF this limit is reached, THE Invitation_Manager SHALL return an `InvitationLimitError` without creating a new invitation.
3. WHEN an invited Family accepts a valid invitation token, THE Invitation_Manager SHALL create a Household_Member record with the `member` role, mark the invitation as accepted, and return the Household identifier, display name, and current active member count.
4. IF the invitation token's validity status is expired, accepted, or revoked at acceptance time, THEN THE Invitation_Manager SHALL return an `InvalidInvitationError` without modifying membership and without marking the invitation as used.
5. IF an accepting Family is already a member of any active Household at acceptance time, THEN THE Invitation_Manager SHALL return a `HouseholdConflictError` without creating a Household_Member record and without marking the invitation as accepted.
6. WHEN a Household_Admin requests to revoke a pending invitation, THE Invitation_Manager SHALL mark the invitation as revoked and prevent future acceptance of that token.
7. IF a Household_Admin requests to revoke an invitation that is already accepted, expired, or revoked, THEN THE Invitation_Manager SHALL return an `InvalidInvitationError` without modifying the invitation record.

---

### Requirement 3: Leave or Disband a Household

**User Story:** As a Household Member, I want to leave a Shared Household, so that my private expenses are no longer included in any shared view.

#### Acceptance Criteria

1. WHEN a non-admin Household_Member requests to leave a Household AND their current net balance is exactly `$0.00`, THE Household_Manager SHALL atomically remove their Household_Member record and delete all `shared_expense_links` belonging to that Family from the Household, preserving the original `gastos` records unchanged, and return a success confirmation; IF either operation fails, THEN THE Household_Manager SHALL roll back both operations and return an error.
2. IF a Household_Member requests to leave a Household and their current net balance is not exactly `$0.00`, THEN THE Household_Manager SHALL return a `BalanceNotZeroError` without modifying any record.
3. IF a Household_Admin requests to leave a Household where at least one other member exists, THEN THE Household_Manager SHALL return an `AdminMustTransferError` without modifying any record.
4. IF a Household_Admin is the only remaining member and requests to leave, THEN THE Household_Manager SHALL atomically set the Household status to `disbanded`, remove all Household_Member records, and delete all `shared_expense_links` for that Household; IF any operation fails, THEN THE Household_Manager SHALL roll back all changes and return an error.
5. IF a Family attempts to leave a Household they do not belong to, THEN THE Household_Manager SHALL return a `NotAMemberError` without modifying any record.
6. WHEN a member voluntarily requests to leave or is removed from a Household for any reason, THE Household_Manager SHALL preserve all `household_settlements` records without modification.
7. WHEN a Household_Admin requests to transfer the `admin` role to another active Household_Member, THE Household_Manager SHALL atomically assign the `admin` role to the target member and assign the `member` role to the requesting Admin.
8. IF a Household_Admin requests to transfer the `admin` role to a Family that is not an active member of the Household, THEN THE Household_Manager SHALL return a `NotAMemberError` without modifying any record.

---

### Requirement 4: Share Individual Expenses with the Household

**User Story:** As a Household Member, I want to mark individual expenses as shared, so that they appear in the consolidated household view.

#### Acceptance Criteria

1. WHEN a Household_Member marks an existing `gastos` record as shared, THE Expense_Sharer SHALL create a `shared_expense_link` record associating the expense with the Household without duplicating the original `gastos` row, and return the new link identifier.
2. IF the `gastos` record targeted for linking does not exist, THEN THE Expense_Sharer SHALL return a `NotFoundError` without creating any record.
3. WHEN a Household_Member attempts to link an expense and the expense's `familia_id` does not match the requesting Family's `familia_id`, THEN THE Expense_Sharer SHALL return an `UnauthorizedError` without creating any link; this authorization check SHALL run before the duplicate-link check.
4. WHEN a Household_Member attempts to share an expense and the same `gasto_id` and `household_id` pair already has an active `shared_expense_link`, THEN THE Expense_Sharer SHALL return a `DuplicateLinkError` without creating a new record.
5. WHEN a Household_Member removes the shared designation from an expense, THE Expense_Sharer SHALL delete the `shared_expense_link` record while leaving the original `gastos` record intact.
6. IF a Household_Member attempts to remove a `shared_expense_link` that does not exist, THEN THE Expense_Sharer SHALL return a `NotFoundError` without modifying any record.
7. THE Expense_Sharer SHALL allow linking an expense at the moment of creation (via an optional `share_with_household: bool` flag, which atomically creates the `gastos` record and the link, rolling back both if either fails) or at any later time while the Family is an active Household member.
8. WHILE a Family is not a member of any active Household, THE Expense_Sharer SHALL return a `NotAMemberError` for any attempt to create or delete a `shared_expense_link`.

---

### Requirement 5: View the Consolidated Household Expense Feed

**User Story:** As a Household Member, I want to see all shared expenses from every member in one feed, so that I have a complete picture of our household spending.

#### Acceptance Criteria

1. WHEN a Household_Member requests the Household expense feed, THE Household_View SHALL return all `gastos` records linked to the Household via `shared_expense_links`, ordered by `fecha` descending.
2. THE Household_View SHALL include, for each shared expense, the originating family's display name, amount, description, category, and date.
3. THE Household_View SHALL support filtering the feed by date range (start date inclusive, end date inclusive) and optionally by a single originating `familia_id` that must be an active member of the Household.
4. THE Household_View SHALL support pagination with a caller-supplied `page_size` between 1 and 100 (inclusive) and a `page` offset, and SHALL return the total count of matching records alongside the page results.
5. IF a non-member requests the Household feed, THEN THE Household_View SHALL return an `UnauthorizedError` with no data structure — the response SHALL NOT include an empty list or any partial data.
6. WHEN the Household has no shared expenses matching the requested filters, THE Household_View SHALL return an empty list with a total count of zero rather than an error.
7. IF a date range filter is supplied where `start_date` is after `end_date`, THEN THE Household_View SHALL return a `ValidationError` without executing the query.

---

### Requirement 6: Household Balance and Debt Tracking

**User Story:** As a Household Member, I want to see how much each person has contributed and what each person owes, so that we can settle up fairly.

#### Acceptance Criteria

1. WHEN a Household_Member requests the Household_Balance for an optional period (start date, end date), THE Balance_Calculator SHALL compute each active member's total shared contributions by summing the `monto` of all their linked `shared_expense_links` whose expense `fecha` falls within the period (or all time if no period is specified).
2. THE Balance_Calculator SHALL compute each member's equal share as `total_household_shared_amount / number_of_active_members` using `Decimal` arithmetic throughout, with no intermediate floating-point conversion.
3. THE Balance_Calculator SHALL compute each member's net balance as `their_contributions − their_equal_share`; a positive net balance means the member is owed money by the group, and a negative net balance means the member owes money to the group.
4. THE Balance_Calculator SHALL include all `household_settlements` within the same period in the computation by adding the settlement `monto` to the payer's effective contributions and subtracting it from the recipient's effective contributions.
5. WHEN the Household_Balance is requested and there are no shared expenses and no settlements in the period, THE Balance_Calculator SHALL return a balance entry of `Decimal("0.00")` for every active member rather than an error.
6. THE Balance_Calculator SHALL recompute the balance on every request by reading the current state of `shared_expense_links` and `household_settlements`; it SHALL NOT persist or return a cached balance.
7. IF a period filter is supplied where `start_date` is after `end_date`, THEN THE Balance_Calculator SHALL return a `ValidationError` without checking for active members or executing any computation.

---

### Requirement 7: Record a Settlement Between Members

**User Story:** As a Household Member, I want to record that I paid another member to settle a debt, so that the balance reflects the payment.

#### Acceptance Criteria

1. WHEN a Household_Member records a Settlement specifying a payer `familia_id`, a recipient `familia_id`, an amount, and a settlement date, THE Settlement_Manager SHALL create a `household_settlements` record with a timestamp, and that record SHALL be included in any subsequent balance computation whose period contains that settlement date.
2. IF the authenticated requesting Family's `familia_id` does not match the payer `familia_id`, THEN THE Settlement_Manager SHALL return an `UnauthorizedError` without creating any record.
3. IF the payer or recipient `familia_id` is not an active member of the same Household, THEN THE Settlement_Manager SHALL return a `NotAMemberError` without creating any record.
4. IF the payer and recipient `familia_id` are the same value, THEN THE Settlement_Manager SHALL return a `ValidationError` without creating any record.
5. IF the settlement `monto` is zero or negative, THEN THE Settlement_Manager SHALL return a `ValidationError` without creating any record; no maximum amount is enforced.
6. WHEN a Settlement record is successfully created, THE Settlement_Manager SHALL emit a `SettlementCreated` event containing the `household_id`, payer `familia_id`, recipient `familia_id`, and `monto` so that downstream handlers (such as AI vector memory) can update asynchronously.

---

### Requirement 8: Household View in the UI

**User Story:** As a Household Member, I want a dedicated section in the app where I can see the shared feed, balances, and settlement options, so that the household information is easy to find.

#### Acceptance Criteria

1. WHEN a logged-in user's session resolves an active Household membership, THE Navigation_Manager SHALL display a "Hogar" navigation item in the main navigation bar.
2. WHEN a logged-in user's session has no active Household membership, THE Navigation_Manager SHALL display a "Crear hogar compartido" entry point in place of the "Hogar" item.
3. WHEN a Household_Member navigates to the Hogar section, THE Household_View SHALL render three tabs in order: "Gastos" (shared expense feed), "Balance" (per-member contributions and net balances), and "Miembros" (member list with invite and leave actions).
4. WHEN a Household_Member successfully marks an expense as shared from the personal Gastos view, THE Household_View SHALL append the new shared expense to the Gastos tab feed without a full page reload, so the entry is visible immediately.
5. THE Household_View SHALL display each active member's family display name alongside their current net balance (formatted as a signed currency value) on the Balance tab.
6. WHEN the Household has no shared expenses, THE Household_View SHALL display an empty-state message on the Gastos tab immediately when the tab loads using locally cached state, before any network confirmation, rather than a blank or error state.
7. WHEN a Household_Member is on the Miembros tab, THE Household_View SHALL show a "Registrar pago" action for each member with a non-zero net balance that opens the Settlement recording form pre-filled with the relevant payer and recipient.

---

### Requirement 9: AI Advisor Household Context

**User Story:** As a Household Member, I want the AI Advisor to answer questions about our shared expenses when I query from the Hogar section, so that I get household-level financial insights.

#### Acceptance Criteria

1. WHEN a Household_Member submits a query from the Hogar section, THE AI_Advisor SHALL scope its vector retrieval exclusively to `ai_vector_memory` records tagged with the current `household_id`, excluding all private expense vectors regardless of `familia_id` membership.
2. THE AI_Advisor SHALL include the originating family's display name as part of the embedded text for each shared expense vector so that the model can attribute expenses to specific members in its response.
3. WHEN a Household_Member submits a query from their personal Contador section, THE AI_Advisor SHALL scope its vector retrieval exclusively to that family's own `ai_vector_memory` records (filtered by `familia_id`), regardless of any active Household membership.
4. WHEN a `shared_expense_link` is created, THE AI_Advisor SHALL asynchronously vectorize the linked `gastos` record using the `nomic-embed-text` embedding pipeline and store the resulting vector in `ai_vector_memory` tagged with both the `familia_id` and the `household_id`.
5. WHEN a `shared_expense_link` is deleted, THE AI_Advisor SHALL asynchronously delete the corresponding household-scoped vector from `ai_vector_memory` (matched by `gasto_id` and `household_id`) to prevent stale retrieval; the family-scoped vector for the same expense SHALL remain untouched.

---

### Requirement 10: Data Privacy and Isolation

**User Story:** As a user, I want my private expenses to remain completely invisible to other household members unless I explicitly share them, so that my financial privacy is respected.

#### Acceptance Criteria

1. THE Data_Isolation_Layer SHALL ensure that every Household query filters results through an inner join on `shared_expense_links`, so that a `gastos` record can only appear in a Household response if a matching `shared_expense_link` row exists for that `household_id`, regardless of the expense's `familia_id`.
2. THE Data_Isolation_Layer SHALL ensure that no Household API endpoint or view returns `gastos`, `ingresos`, or `categorias_gastos` records that belong to a Family not currently a member of the queried Household.
3. WHEN an authenticated user submits any Household operation, THE Data_Isolation_Layer SHALL verify that the user's `familia_id` is an active member of the target `household_id` before executing the operation, returning an `UnauthorizedError` on failure; unauthenticated requests SHALL be rejected before this membership check is performed.
4. THE Data_Isolation_Layer SHALL reject any write to `shared_expense_links` where the `familia_id` on the targeted `gastos` record does not match the authenticated user's `familia_id`, returning an `UnauthorizedError` without persisting changes.
5. THE Data_Isolation_Layer SHALL append an audit log entry to a dedicated `household_audit_log` table for every `shared_expense_link` creation and deletion, capturing `familia_id`, `gasto_id`, `household_id`, action (`created` or `deleted`), and `timestamp`.
