# Property Backend API — Async FastAPI Day 1–6 Package

This package contains the backend implementation from Day 1 through Day 6, excluding Day 4 Paystack integration because Paystack account details are not available yet.

Stack:

```txt
FastAPI
SQLAlchemy 2.0 Async ORM
asyncpg
Alembic async migrations
Supabase PostgreSQL
Supabase Storage
JWT authentication
Argon2 password hashing
Role-based access control
```

## Included scope

```txt
Day 1 — Async FastAPI foundation, Supabase PostgreSQL, Alembic, health/status endpoints
Day 2 — Auth, JWT, refresh tokens, logout, password reset foundation, role guards
Day 3 — Agent profile, admin approval/rejection/disable/enable, admin logs
Day 4 — Not included yet; pending Paystack account details
Day 5 — Property CRUD, approved-agent protection, Supabase Storage image upload, soft delete
Day 6 — Property search/filtering/pagination and admin property moderation
```

## Implemented endpoints

### Core

```txt
GET /health
GET /api/v1/health
GET /api/v1/status
```

### Auth

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

### Agent

```txt
POST  /api/v1/agents/me
GET   /api/v1/agents/me
PATCH /api/v1/agents/me
GET   /api/v1/agents/me/properties
```

### Public properties

```txt
POST   /api/v1/properties
GET    /api/v1/properties
GET    /api/v1/properties/search
GET    /api/v1/properties/{property_id}
PATCH  /api/v1/properties/{property_id}
DELETE /api/v1/properties/{property_id}
POST   /api/v1/properties/{property_id}/media
DELETE /api/v1/properties/{property_id}/media/{media_id}
```

### Admin

```txt
GET    /api/v1/admin/agents
GET    /api/v1/admin/agents/{agent_id}
PATCH  /api/v1/admin/agents/{agent_id}/approve
PATCH  /api/v1/admin/agents/{agent_id}/reject
PATCH  /api/v1/admin/agents/{agent_id}/disable
PATCH  /api/v1/admin/agents/{agent_id}/enable

GET    /api/v1/admin/properties
GET    /api/v1/admin/properties/{property_id}
PATCH  /api/v1/admin/properties/{property_id}/hide
PATCH  /api/v1/admin/properties/{property_id}/restore
DELETE /api/v1/admin/properties/{property_id}

GET    /api/v1/admin/activity-logs
```

## Setup

Create virtual environment:

```bash
python -m venv .venv
```

Windows PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

Mac/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create `.env`:

```bash
cp .env.example .env
```

Generate JWT secret:

```bash
python scripts/generate_secret.py
```

Paste the generated value into:

```env
JWT_SECRET_KEY="..."
```

Update Supabase values in `.env`:

```env
DATABASE_URL="postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require"
SUPABASE_URL="https://<project-ref>.supabase.co"
SUPABASE_SERVICE_ROLE_KEY="<service-role-key>"
SUPABASE_STORAGE_BUCKET="property-media"
```

Recommended Supabase database connection:

```txt
Session Pooler, port 5432
```

Run migrations:

```bash
alembic upgrade head
```

Create first super admin:

```bash
python scripts/create_super_admin.py admin@example.com "Admin Name" "StrongPassword123!"
```

Run server:

```bash
uvicorn app.main:app --reload
```

Open Swagger:

```txt
http://localhost:8000/docs
```

## Supabase Storage setup for Day 5/6

Create a public bucket in Supabase:

```txt
Bucket name: property-media
Public: true
Allowed image types: image/jpeg, image/png, image/webp
Recommended max file size: 5 MB
```

The backend validates:

```txt
JPEG, PNG, WEBP only
5 MB max image size
10 images max per property
```

## Temporary Paystack bypass

Paystack is not implemented yet because account keys are pending. For development testing only:

```bash
python scripts/mark_agent_paid.py "<agent_profile_id>"
```

Then approve the agent through the admin API:

```txt
PATCH /api/v1/admin/agents/{agent_id}/approve
```

Do not manually switch agents directly to APPROVED unless debugging. Test the admin approval workflow through the backend.

## Day 6 search examples

Public search:

```txt
GET /api/v1/properties/search?state=Lagos&category=LAND&min_price=5000000&page=1&limit=20
```

Sort options:

```txt
newest
oldest
price_asc
price_desc
```

Supported filters:

```txt
q
country
state
local_government
community
min_price
max_price
category
listing_type
status
sort
page
limit
```

Admin property list:

```txt
GET /api/v1/admin/properties?status=HIDDEN&include_deleted=false&page=1&limit=20
```

Admin hide property:

```txt
PATCH /api/v1/admin/properties/{property_id}/hide
```

Admin restore property:

```txt
PATCH /api/v1/admin/properties/{property_id}/restore
```

Admin soft delete property:

```txt
DELETE /api/v1/admin/properties/{property_id}?note=Fraudulent%20listing
```

## Production notes

- Password reset currently returns debug token/OTP in development only. Connect email/SMS before production.
- Add real frontend/mobile URLs to `ALLOWED_ORIGINS`.
- Store secrets in Render/Supabase environment variables, not Git.
- Do not expose the Supabase service role key to mobile or web apps.
- Mobile and web clients must call FastAPI only. They should not write directly to Supabase tables.
