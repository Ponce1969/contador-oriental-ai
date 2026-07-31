# Tasks: Password Recovery

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 600-800 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (infra+models+repo) → PR 2 (service+email+UI) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Migration, models, repository, dependency | PR 1 | base: main; self-contained infra |
| 2 | Service logic, email service, controllers, views, routes | PR 2 | base: PR 1 branch; depends on Unit 1 |
| 3 | Tests for all layers | PR 2 | bundled with Unit 2 (tests are proportional) |

## Phase 1: Infrastructure & Models

- [ ] 1.1 Add `resend` to `pyproject.toml` dependencies and run `uv sync`
- [ ] 1.2 Add `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `APP_BASE_URL` to `.env.example`
- [ ] 1.3 Create `migrations/014_add_password_recovery.py` — add `email VARCHAR(100) UNIQUE` to `usuarios`, create `password_reset_tokens` table with indexes
- [ ] 1.4 Create `models/password_reset_model.py` — `PasswordResetToken` Pydantic model with fields: id, user_id, token, expires_at, used_at, created_at
- [ ] 1.5 Modify `models/user_model.py` — add `email: str | None` to `User`, add `email: str` to `UserCreate`
- [ ] 1.6 Add `PasswordResetTokensTable` to `database/tables.py`
- [ ] 1.7 Create `repositories/password_reset_repository.py` — `create_token()`, `find_valid_token()`, `mark_used()` with existing session pattern
- [ ] 1.8 Add `get_by_email()` to `repositories/user_repository.py` — query by email, return `Result[User, DatabaseError]`

## Phase 2: Core Logic & Email Service

- [ ] 2.1 Create `services/infrastructure/email_service.py` — `EmailService` Protocol + `ResendEmailService` implementation using `resend` SDK, `RESEND_FROM_EMAIL` and `APP_BASE_URL` from env
- [ ] 2.2 Add `request_password_reset(self, email: str) -> Result[str, AppError]` to `services/domain/auth_service.py` — rate limit via email key (3/15min), find user, generate token (`secrets.token_urlsafe(32)`), store token, send email, always return generic message
- [ ] 2.3 Add `reset_password(self, token: str, new_password: str) -> Result[None, AppError]` to `services/domain/auth_service.py` — validate token (not expired, not used), hash new password with Argon2id, update password, mark token used
- [ ] 2.4 Create `controllers/auth_controller.py` methods — `request_password_reset(email)` and `reset_password(token, new_password)`, delegating to AuthService

## Phase 3: UI & Routing

- [ ] 3.1 Add "¿Olvidaste tu contraseña?" link to `views/pages/login_view.py` below password field, navigating to `/forgot-password`
- [ ] 3.2 Create `views/pages/forgot_password_view.py` — email input, submit button, generic confirmation message, rate-limit error display
- [ ] 3.3 Create `views/pages/reset_password_view.py` — new password + confirm password fields, token from `page.query_params`, invalid/expired/used token error messages, success → redirect to login
- [ ] 3.4 Add `/forgot-password` and `/reset-password` routes to `configs/routes.py`

## Phase 4: Testing

- [ ] 4.1 Create `tests/test_password_reset.py` — test `PasswordResetRepository` CRUD (create, find valid, mark used, expired tokens, used tokens)
- [ ] 4.2 Add tests to `tests/test_auth_service.py` — `request_password_reset` (existing email, non-existing email, rate-limited) and `reset_password` (valid token, expired token, used token, invalid token, short password)
- [ ] 4.3 Create `tests/test_email_service.py` — mock `ResendEmailService`, test email sending success and failure
- [ ] 4.4 Add `email` field tests to relevant registration tests — new registration requires email, duplicate email rejected