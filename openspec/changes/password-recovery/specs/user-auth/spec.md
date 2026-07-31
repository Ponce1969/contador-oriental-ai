# Delta for user-auth

## MODIFIED Requirements

### Requirement: User Registration

New user registration MUST require an email address. The email field is mandatory for new registrations and MUST be unique across all users.

(Previously: Registration only required username, password, and family info — no email on User model)

#### Scenario: Successful registration with email

- GIVEN no user with email "new@example.com" exists
- WHEN a new user registers with email "new@example.com", username "newuser", and password "pass123"
- THEN the user is created with email stored in `usuarios.email`
- AND the email is validated to contain "@" character

#### Scenario: Duplicate email registration

- GIVEN a user with email "existing@example.com" already exists
- WHEN a new registration attempts to use "existing@example.com"
- THEN the system rejects with "El email ya está registrado"

#### Scenario: Missing email on registration

- GIVEN a new registration attempt
- WHEN the email field is empty or null
- THEN the system rejects with "El email es obligatorio"

### Requirement: User Model Update

The User model MUST include an `email` field (nullable for backward compatibility, unique when not null). The UserCreate model MUST include `email` as a required field.

(Previously: User model had no email field; UserCreate had no email field)

#### Scenario: Existing user without email

- GIVEN a user created before the email feature was added
- WHEN the user attempts to request a password reset
- AND their email field is NULL
- THEN the system cannot send a reset email
- AND the user still sees the generic confirmation message

#### Scenario: UserRepository lookup by email

- GIVEN a user with email "user@example.com" exists
- WHEN `UserRepository.get_by_email("user@example.com")` is called
- THEN it returns the user

#### Scenario: UserRepository lookup for non-existing email

- GIVEN no user with email "nobody@example.com" exists
- WHEN `UserRepository.get_by_email("nobody@example.com")` is called
- THEN it returns an Err with "Usuario no encontrado"