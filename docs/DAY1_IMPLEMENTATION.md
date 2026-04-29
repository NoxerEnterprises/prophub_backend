# Day 1 Implementation Notes

## Purpose

Day 1 establishes the backend foundation so the rest of the sprint can be built without architectural chaos.

## Implemented

1. FastAPI app factory
2. `/api/v1` API prefix
3. Health and status endpoints
4. Environment variable configuration
5. Supabase PostgreSQL connection helper
6. SQLAlchemy base and session management
7. Initial models:
   - User
   - AgentProfile
   - AdminProfile
8. Initial Alembic migration
9. CORS setup
10. Standard response format
11. Global exception handlers
12. Dockerfile
13. Render blueprint
14. Smoke tests

## Database Tables Created

### users

Stores all platform identities. Later sprint days will add registration, login, JWT, refresh tokens, and password reset.

### agent_profiles

Stores agent-specific data and approval status.

### admin_profiles

Stores admin-specific data.

## Important architecture rule

The frontend should not directly write to Supabase. The mobile app should call FastAPI, and FastAPI should enforce all business rules before writing to Supabase PostgreSQL.

```txt
Mobile App → FastAPI → Supabase PostgreSQL
```

## Day 2 continuation

Day 2 should build:

- Registration
- Login
- Password hashing
- JWT access token
- JWT refresh token
- Auth dependencies
- Role guards
- Password reset foundation
