# Password Recovery Specification

## Purpose

Email-based password recovery for users who forgot their password. Uses Resend API for email delivery and one-time-use tokens with 1-hour expiration.

## Requirements

### Requirement: Password Reset Request

The system MUST allow users to request a password reset by submitting their email address.

- The system SHALL accept an email address on the `/forgot-password` page.
- The system SHALL always respond with the same generic message regardless of whether the email exists: "Si tu email está registrado, recibirás un link para resetear tu contraseña."
- The system MUST NOT reveal whether an email is registered (email enumeration protection).
- The system SHALL generate a cryptographically secure token using `secrets.token_urlsafe(32)`.
- The system MUST store the token in `password_reset_tokens` with user_id, token, and expires_at (1 hour from creation).
- The system SHALL send an email via Resend to `pedidos@loquinto.com` containing a reset link with the token as a URL parameter.
- The reset link MUST use `APP_BASE_URL` env var as the base URL: `{APP_BASE_URL}/reset-password?token={token}`.
- The system SHOULD rate-limit reset requests per email (max 3 per 15 minutes) to prevent abuse.

#### Scenario: Successful reset request for existing email

- GIVEN a user with email "user@example.com" exists in the system
- WHEN the user submits "user@example.com" on the forgot-password page
- THEN a reset token is created with 1-hour expiration
- AND an email is sent to "user@example.com" with a reset link
- AND the response shows the generic confirmation message

#### Scenario: Reset request for non-existing email

- GIVEN no user with email "nobody@example.com" exists
- WHEN the user submits "nobody@example.com" on the forgot-password page
- THEN no token is created and no email is sent
- AND the response shows the SAME generic confirmation message (no disclosure)

#### Scenario: Rate limit exceeded

- GIVEN the user has submitted 3 reset requests for the same email within 15 minutes
- WHEN the user submits a 4th request
- THEN the system rejects the request with a rate-limit message
- AND no new token or email is generated

### Requirement: Password Reset Execution

The system MUST allow users to set a new password using a valid reset token.

- The system SHALL validate that the token exists, has not been used (`used_at IS NULL`), and has not expired (`expires_at > NOW()`).
- The system MUST mark the token as used (`used_at = NOW()`) upon successful password reset.
- The system SHALL use Argon2id to hash the new password (same as registration).
- The new password MUST be at least 6 characters long.
- The system MUST update `usuarios.password_hash` with the new hash.
- After successful reset, the system SHALL redirect the user to the login page with a success message.

#### Scenario: Successful password reset

- GIVEN a valid, unused, non-expired token exists for a user
- WHEN the user submits a new password (≥ 6 chars) via the reset-password page
- THEN the password is updated
- AND the token is marked as used (used_at set to NOW)
- AND the user is redirected to login with a success message

#### Scenario: Expired token

- GIVEN a token with expires_at in the past
- WHEN the user attempts to reset their password
- THEN the system rejects the request with "El link ha expirado. Solicitá uno nuevo."
- AND the token is NOT marked as used

#### Scenario: Already-used token

- GIVEN a token with used_at already set
- WHEN the user attempts to reset their password
- THEN the system rejects the request with "Este link ya fue utilizado. Solicitá uno nuevo."

#### Scenario: Invalid token

- GIVEN a token that does not exist in the database
- WHEN the user attempts to reset their password
- THEN the system rejects the request with "Link inválido."

#### Scenario: New password too short

- GIVEN a valid token
- WHEN the user submits a new password with fewer than 6 characters
- THEN the system rejects the request with "La contraseña debe tener al menos 6 caracteres"
- AND the token remains unused

### Requirement: Reset Token Lifecycle

- Tokens MUST expire 1 hour after creation.
- Tokens MUST be single-use: once used, `used_at` is set and the token cannot be reused.
- Each token MUST be unique (enforced by UNIQUE constraint on token column).
- Multiple tokens MAY exist for the same user (from multiple reset requests), but only the most recent unused one is typically used.

### Requirement: Email Delivery via Resend

- The system SHALL use the Resend Python SDK to send password reset emails.
- Emails MUST be sent from `RESEND_FROM_EMAIL` env var (default: `pedidos@loquinto.com`).
- The email subject SHOULD be "Recuperá tu contraseña — Contador Oriental".
- The email body MUST contain the reset link with the token.
- If Resend fails to send the email, the system SHALL log the error and return a generic message (no error disclosure to user).

#### Scenario: Resend API failure

- GIVEN a valid user email and token created successfully
- WHEN the Resend API call fails (network error, API key invalid, etc.)
- THEN the error is logged
- AND the user still sees the generic confirmation message (no error disclosure)
- AND the token remains in the DB (user can request a new one)

### Requirement: Forgot Password UI

- The login page MUST show a "¿Olvidaste tu contraseña?" link below the password field.
- Clicking the link navigates to `/forgot-password`.
- The forgot-password page MUST have a single email input field and a submit button.
- The page MUST return to the login page after submission (with the generic message).

### Requirement: Reset Password UI

- The `/reset-password` page MUST accept a `token` URL parameter.
- If no token is present in the URL, the page MUST show "Link inválido" and redirect to `/forgot-password`.
- The page MUST have a new password field and a confirm password field.
- Both password fields MUST match before submission.
- Submitting redirects to `/login` on success.