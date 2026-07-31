# Design: Password Recovery

## Technical Approach

Add email to `usuarios`, create `password_reset_tokens` table, integrate Resend SDK for email delivery. Extend `AuthService` with reset methods. New views for forgot/reset password flow follow existing `LoginView`/`RegisterView` patterns. Rate limiting reuses existing `RateLimiter`.

## Architecture Decisions

### Decision: Token Storage

**Choice**: PostgreSQL `password_reset_tokens` table
**Alternatives considered**: Redis, in-memory dict
**Rationale**: Project uses PostgreSQL exclusively. Tokens need persistence across app restarts. Family app — volume justifies simple DB approach.

### Decision: Email Per User (not per Family)

**Choice**: Add nullable `email` column to `usuarios`
**Alternatives considered**: Use `familias.email`, separate `user_emails` table
**Rationale**: Each user must have their own email for password recovery. Using family email means any member can reset another's password — security hazard. Nullable for backward compat; required for new registrations.

### Decision: Email Service Interface

**Choice**: Protocol-based interface `EmailService` with `ResendEmailService` implementation
**Alternatives considered**: Direct Resend calls in AuthService
**Rationale**: Testability — tests mock the protocol without hitting Resend. Follows hexagonal architecture principle used in the project.

### Decision: Rate Limiting for Reset Requests

**Choice**: Reuse existing `RateLimiter` from `core/security.py` with email-based keys
**Alternatives considered**: Separate in-memory tracker, no rate limiting
**Rationale**: `RateLimiter` already handles per-key tracking with configurable thresholds. Use email as key, separate bucket from login attempts.

## Data Flow

```
User clicks "Forgot password?"
         │
         ▼
ForgotPasswordView → AuthController.request_password_reset(email)
         │
         ▼
AuthService.request_password_reset(email)
    ├── RateLimiter check (email key, 3/15min)
    ├── UserRepository.get_by_email(email)
    │   └── If not found: return Ok with generic message (no disclosure)
    ├── Generate token: secrets.token_urlsafe(32)
    ├── PasswordResetRepository.create(user_id, token, expires_at=now+1h)
    ├── EmailService.send_password_reset(email, token)
    │   └── Resend API: POST /emails
    └── Return Ok("Si tu email está registrado...")

User clicks reset link in email
         │
         ▼
ResetPasswordView?token=XXX → AuthController.reset_password(token, new_password)
         │
         ▼
AuthService.reset_password(token, new_password)
    ├── PasswordResetRepository.find_valid_token(token)
    │   └── Check: exists, not used (used_at IS NULL), not expired
    ├── Hash new password with Argon2id
    ├── UserRepository.update_password(user_id, new_hash)
    ├── PasswordResetRepository.mark_used(token)
    └── Return Ok → redirect to /login
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `models/password_reset_model.py` | Create | Pydantic model: PasswordResetToken |
| `models/user_model.py` | Modify | Add `email: str \| None` to User, `email: str` to UserCreate |
| `models/errors.py` | Modify | No changes needed — reuse ValidationError, DatabaseError |
| `repositories/password_reset_repository.py` | Create | CRUD: create_token, find_valid_token, mark_used |
| `repositories/user_repository.py` | Modify | Add `get_by_email()`, update `add()` to include email |
| `services/domain/auth_service.py` | Modify | Add `request_password_reset()`, `reset_password()` |
| `services/infrastructure/email_service.py` | Create | Protocol + ResendEmailService implementation |
| `controllers/auth_controller.py` | Modify | Add forgot/reset controller methods |
| `views/pages/forgot_password_view.py` | Create | Email input form, generic confirmation message |
| `views/pages/reset_password_view.py` | Create | New password + confirm, token from URL param |
| `views/pages/login_view.py` | Modify | Add "¿Olvidaste tu contraseña?" link |
| `configs/routes.py` | Modify | Add /forgot-password and /reset-password routes |
| `migrations/014_add_password_recovery.py` | Create | Add email to usuarios, create password_reset_tokens |
| `database/tables.py` | Modify | Add PasswordResetTokensTable, add email to UsuarioTable (if exists) |
| `pyproject.toml` | Modify | Add `resend` dependency |
| `.env.example` | Modify | Add RESEND_API_KEY, RESEND_FROM_EMAIL, APP_BASE_URL |
| `tests/test_auth_service.py` | Modify | Add tests for reset flow |
| `tests/test_password_reset.py` | Create | Full test coverage for token CRUD, reset flow, rate limiting |
| `tests/test_email_service.py` | Create | Mock-based tests for email service |

## Interfaces / Contracts

```python
# models/password_reset_model.py
class PasswordResetToken(BaseModel):
    id: int | None = None
    user_id: int
    token: str
    expires_at: datetime
    used_at: datetime | None = None
    created_at: datetime | None = None

# services/infrastructure/email_service.py
class EmailService(Protocol):
    def send_password_reset(self, to_email: str, reset_url: str) -> Result[None, str]: ...

class ResendEmailService:
    def __init__(self) -> None:
        self._api_key = os.getenv("RESEND_API_KEY")
        self._from_email = os.getenv("RESEND_FROM_EMAIL", "pedidos@loquinto.com")

# AuthService additions
def request_password_reset(self, email: str) -> Result[str, AppError]: ...
def reset_password(self, token: str, new_password: str) -> Result[None, AppError]: ...
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | PasswordResetRepository CRUD | Transaction rollback tests (real PG) |
| Unit | AuthService.request_password_reset | Mock EmailService + UserRepository, test all scenarios |
| Unit | AuthService.reset_password | Mock PasswordResetRepository, test expired/used/invalid tokens |
| Unit | ResendEmailService | Mock Resend API responses |
| Integration | Full reset flow | End-to-end: create token → find valid → reset password → verify used |
| Edge | Rate limiting on reset requests | Test RateLimiter with email keys |

## Migration / Rollout

Migration 014 adds:
1. `ALTER TABLE usuarios ADD COLUMN email VARCHAR(100) UNIQUE;` — nullable, no data loss
2. `CREATE TABLE password_reset_tokens (...)` — new table, no existing data affected

Rollback: Migration 014 `down()` drops the table and column. Safe — no production data dependency.

New dependency: `resend` added to pyproject.toml. Requires `uv sync` on the server.

## Open Questions

- None — all decisions resolved during proposal phase.