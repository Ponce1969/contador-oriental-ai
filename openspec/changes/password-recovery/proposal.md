# Proposal: Password Recovery

## Intent

Users who forget their password cannot regain access. The only option is creating a new account, which is unprofessional and loses all historical data. This change adds email-based password recovery using the Resend API.

## Scope

### In Scope
- `email` column on `usuarios` table (nullable for existing users, mandatory for new registrations)
- `password_reset_tokens` table (one-time-use tokens, 1h expiry)
- Resend email service (from `pedidos@loquinto.com`)
- "Forgot password?" flow: email input → generic confirmation → token link → new password
- Registration updated: email field mandatory for new users

### Out of Scope
- Profile page for existing users to add/update email (future enhancement)
- Admin UI to manage users
- Automated cleanup of expired tokens (future cron/cleanup)
- Password change while logged in (already exists as `change_password`)

## Capabilities

### New Capabilities
- `password-recovery`: Full email-based password reset flow with Resend — request, token generation, email delivery, token validation, password update

### Modified Capabilities
- `user-auth`: Add `email` field to User/UserCreate models; make email mandatory for new registrations; update UserRepository with `get_by_email()`

## Approach

Add `email` column (nullable, unique) to `usuarios` and a `password_reset_tokens` table. Integrate Resend Python SDK for email delivery. Extend AuthService with `request_password_reset(email)` and `reset_password(token, new_password)`. Add two new routes (`/forgot-password`, `/reset-password`) and views. Use `secrets.token_urlsafe(32)` for cryptographic tokens. Enforce email enumeration protection (same generic response regardless of email existence). Rate-limit reset requests.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `models/user_model.py` | Modified | Add `email` field to User, UserCreate |
| `models/password_reset_model.py` | New | PasswordResetToken model |
| `repositories/user_repository.py` | Modified | Add `get_by_email()` |
| `repositories/password_reset_repository.py` | New | Token CRUD (create, find, mark used) |
| `services/domain/auth_service.py` | Modified | Add request_password_reset, reset_password |
| `services/infrastructure/email_service.py` | New | Resend SDK integration, mockable for tests |
| `controllers/auth_controller.py` | Modified | Add forgot/reset controller methods |
| `views/pages/login_view.py` | Modified | Add "Forgot password?" link |
| `views/pages/forgot_password_view.py` | New | Email input form |
| `views/pages/reset_password_view.py` | New | New password form (receives token via URL param) |
| `configs/routes.py` | Modified | Add /forgot-password and /reset-password routes |
| `migrations/014_*.py` | New | Add email column + password_reset_tokens table |
| `database/tables.py` | Modified | Add PasswordResetTokens table definition |
| `pyproject.toml` | Modified | Add `resend` dependency |
| `.env.example` | Modified | Add RESEND_API_KEY, RESEND_FROM_EMAIL, APP_BASE_URL |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Existing users have no email — cannot recover until they add it | High | Acceptable: nullable column, future profile page can add it |
| Flet web deep linking for reset URL | Med | Use APP_BASE_URL env var (same pattern as OCR_API_PUBLIC_URL) |
| Resend free tier limit (100 emails/day) | Low | Sufficient for family app; monitor if needed |
| Token accumulation in DB | Low | Low volume app; future cleanup job if needed |

## Rollback Plan

1. Remove `/forgot-password` and `/reset-password` routes
2. Revert migration 014 (drops email column + tokens table)
3. Remove `resend` from pyproject.toml
4. All changes are additive — rollback is safe with no data loss beyond the email column values

## Dependencies

- `resend` Python SDK (pip install resend)
- Resend account with `pedidos@loquinto.com` verified (already configured in production)
- Cloudflare domain DNS already configured for Resend

## Success Criteria

- [ ] User can click "Forgot password?", enter email, receive reset link via Resend
- [ ] Reset link opens form to set new password
- [ ] Token expires after 1 hour, is single-use
- [ ] Existing users without email see a message directing them to add email first
- [ ] New registrations require email
- [ ] Email enumeration protection: same generic message for existing/non-existing emails
- [ ] All new and modified code has tests