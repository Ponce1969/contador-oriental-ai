# Exploration: Password Recovery via Resend

**Change**: password-recovery
**Date**: 2026-06-13
**Status**: Explored

## Current State

The app has a multi-user auth system with `familias` (family groups) and `usuarios` (users). Passwords are hashed with Argon2id. There is a rate limiter (5 attempts / 15 min) and session timeout (8h). **There is NO password recovery mechanism** — users who forget their password cannot regain access. The only option is creating a new account, which is unprofessional and loses all historical data.

The production server (Orange Pi) has `RESEND_API_KEY` already configured in its `.env`. The `resend` Python SDK is NOT yet in `pyproject.toml`.

### Current Auth Flow
- Login → `AuthController.login()` → `AuthService.login()` → `UserRepository` → PostgreSQL
- Registration → `RegistrationController` → `RegistrationService` → creates family + admin user
- Password change → `AuthService.change_password()` (requires old password — useless if forgotten)

### Email Location Problem
- `familias.email` — shared email for the family, NOT per-user. Every family member would see the same email. Cannot use this for per-user password reset.
- `usuarios` table — has NO email column. Needs migration.

## Affected Areas

- `models/user_model.py` — Add `email` field to `User` and `UserCreate`
- `repositories/user_repository.py` — Add `get_by_email()`, update user creation to include email
- `services/domain/auth_service.py` — Add `request_password_reset()` and `reset_password()` methods
- `controllers/auth_controller.py` — Add controller methods for reset flow
- `views/pages/login_view.py` — Add "Forgot password?" link
- `configs/routes.py` — Add `/forgot-password` and `/reset-password` routes
- `migrations/` — New migration 014 for email column + reset tokens table
- `database/tables.py` — Add `password_reset_tokens` table definition
- `pyproject.toml` — Add `resend` dependency
- `.env` / `.env.example` — Add `RESEND_API_KEY` and `RESEND_FROM_EMAIL`
- New files: `models/password_reset_model.py`, `repositories/password_reset_repository.py`, `services/infrastructure/email_service.py`, `views/pages/forgot_password_view.py`, `views/pages/reset_password_view.py`

## Approaches

### 1. Email in `usuarios` table + DB tokens (RECOMMENDED)

Add `email` column directly to `usuarios` table, create `password_reset_tokens` table for tokens.

**Pros:**
- Consistent with existing project pattern (everything in PostgreSQL)
- Simple to query: `SELECT * FROM usuarios WHERE email = ?`
- Tokens in DB allow easy expiration and one-time-use enforcement
- Follows existing repository pattern
- Migration is straightforward

**Cons:**
- Requires DB migration (but project already has 13 migrations)
- Email column initially nullable (existing users don't have emails yet)
- Slightly more migration work than in-memory tokens

**Effort:** Medium

### 2. Email via `familias` link (NOT RECOMMENDED)

Use the family email to send reset links. All family members share one email.

**Pros:**
- No migration needed for email column
- Simpler initially

**Cons:**
- **SECURITY HAZARD**: Anyone in the family can reset anyone else's password
- Cannot identify individual users
- Family email is optional (`email: str | None`)
- Unprofessional — real apps need per-user emails

**Effort:** Low (but wrong approach)

### 3. Separate `user_emails` table

Create a separate table linking users to emails instead of adding a column.

**Pros:**
- Normalized design
- Could support multiple emails per user in the future

**Cons:**
- Over-engineered for a simple feature
- Adds complexity to every user query
- Goes against the project's simple SQL pattern

**Effort:** Medium-High

## Recommendation

**Approach 1: Email in `usuarios` table + DB token table**

This is the right approach because:
1. Per-user email is a basic requirement for password recovery
2. PostgreSQL token storage matches the project's existing pattern (no Redis)
3. Simple migration path: add nullable email column, create tokens table
4. Registration service already validates email format — reuse that pattern
5. Easy to enforce: one-time-use tokens, expiration, rate limiting

## Detailed Design Notes

### Migration 014

```sql
-- Add email to usuarios (nullable, unique)
ALTER TABLE usuarios ADD COLUMN email VARCHAR(100) UNIQUE;

-- Create password_reset_tokens table
CREATE TABLE password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_password_reset_tokens_token ON password_reset_tokens(token);
CREATE INDEX idx_password_reset_tokens_user_id ON password_reset_tokens(user_id);
```

### Email Service

```python
# services/infrastructure/email_service.py
# Uses Resend SDK (https://resend.com/docs/send-with-python)
# - send_password_reset_email(to_email, reset_url)
# - Mockable for tests (interface + Resend implementation)
```

### Token Generation

```python
# Use secrets.token_urlsafe(32) for cryptographic randomness
# Token expires in 1 hour
# One-time-use: mark as used after password reset
```

### Reset Flow

1. User clicks "Forgot password?" on login page
2. Enters email address
3. System shows: "If an account with that email exists, a reset link has been sent."
4. If email exists: `AuthService.request_password_reset(email)` → generate token → send email via Resend
5. Email contains link: `https://app-domain/reset-password?token=XXX`
6. User clicks link → ResetPasswordView shows new password form
7. `AuthService.reset_password(token, new_password)` → validate token (not expired, not used) → update password → mark token used

### Security Considerations

- Rate limit reset requests (extend existing RateLimiter or add separate limiter)
- Token expiry: 1 hour
- One-time use: tokens are marked `used_at` after successful reset
- Email enumeration protection: always show same message regardless of email existence
- Clean up expired tokens periodically (optional, can be a future enhancement)

### Flet Web Consideration

Since this is a Flet web app, the reset password link in the email needs to point to a URL that the Flet router can handle. The `/reset-password?token=XXX` route must be accessible without authentication.

### Testing Strategy

1. **Unit tests** for `PasswordResetRepository` (CRUD operations)
2. **Unit tests** for `AuthService.request_password_reset()` and `AuthService.reset_password()`
3. **Unit tests** for `EmailService` (mocked Resend)
4. **Integration tests** for full reset flow
5. **Test that expired tokens are rejected**
6. **Test that used tokens are rejected**
7. **Test email enumeration protection** (same response for existing/non-existing emails)

## Risks

1. **Existing users without email**: Migration adds nullable column. Users created before this feature won't have emails. They'll need to update their profile. This is an acceptable tradeoff.
2. **Flet deep linking**: The reset URL must work in Flet web mode. Need to verify that `page.route` or query parameters are accessible on app load.
3. **Resend free tier limits**: Resend's free plan allows 100 emails/day and 3,000/month. For a family app, this is more than enough.
4. **Token cleanup**: Expired tokens accumulate in DB. A cleanup job could be added later, but it's not critical for a family app.

## Ready for Proposal

**Yes.** The exploration is complete and the recommended approach is clear. The orchestrator should proceed to `sdd-propose` to create a formal proposal for this change.