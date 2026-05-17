# Day 2 Implementation Notes — Authentication, JWT, Roles, Password Reset Foundation

## Implemented

1. Public registration endpoint
2. Login endpoint
3. Argon2 password hashing via `pwdlib`
4. JWT access token generation
5. Secure refresh token generation and storage
6. Refresh token rotation
7. Logout endpoint with single-session or all-sessions revocation
8. Current user endpoint
9. Role-based dependency guards
10. Password reset request/verify/reset foundation
11. Token tables and Alembic migration
12. Super admin creation script
13. Secret key generation script

## New API endpoints

```txt
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
GET  /api/v1/auth/me
POST /api/v1/auth/request-reset
POST /api/v1/auth/verify-reset
POST /api/v1/auth/reset-password
```

## Debug role-guard endpoints

These exist only to prove role-based access works during development:

```txt
GET /api/v1/debug/roles/protected
GET /api/v1/debug/roles/agent
GET /api/v1/debug/roles/admin
GET /api/v1/debug/roles/super-admin
```

You can remove these before production if you do not want test endpoints exposed.

## New database tables

```txt
refresh_tokens
password_reset_tokens
```

## Password reset limitation

The backend generates and stores reset tokens/OTPs securely, but it does not send emails or SMS yet. The client must provide an email/SMS provider later.

In development mode (`DEBUG=true`), `/auth/request-reset` returns the raw reset token and OTP so the developer can test the full flow.

In production mode (`DEBUG=false`), the raw token and OTP are not returned. A real email/SMS delivery service must be connected before enabling production password reset.

## Security rules

1. Passwords are hashed using Argon2.
2. Refresh tokens are stored as deterministic SHA-256 hashes, not raw tokens.
3. Password reset tokens and OTPs are stored as hashes, not raw values.
4. Refresh tokens rotate on every refresh.
5. Password reset invalidates all active refresh tokens for the user.
6. Public users cannot create ADMIN or SUPER_ADMIN accounts through registration.
7. Protected endpoints require a Bearer access token.

## Manual tasks required

### 1. Add JWT secret to `.env`

Generate a secret:

```bash
python scripts/generate_secret.py
```

Copy the output into `.env`:

```env
JWT_SECRET_KEY="paste-generated-secret-here"
```

### 2. Run migrations

```bash
alembic upgrade head
```

Expected new Supabase tables:

```txt
refresh_tokens
password_reset_tokens
```

### 3. Create first super admin

After migrations:

```bash
python scripts/create_super_admin.py admin@example.com "Admin Name" "StrongPassword123!"
```

Use a real secure password.

### 4. Test auth flow in Swagger

Open:

```txt
http://localhost:8000/docs
```

Test in this order:

1. Register user
2. Login user
3. Copy access token
4. Click Authorize in Swagger
5. Paste access token
6. Call `/api/v1/auth/me`
7. Call `/api/v1/auth/refresh`
8. Call `/api/v1/auth/logout`

## Day 3 continuation

Day 3 should build agent profile expansion, agent status management, admin controls, and admin activity logging.
