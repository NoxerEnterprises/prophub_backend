# Property Backend API — Day 1 Foundation

This is the Day 1 backend foundation for a mobile-first property listing platform.

## Stack

- FastAPI
- Supabase PostgreSQL
- SQLAlchemy 2.0
- Alembic migrations
- Pydantic Settings
- Uvicorn
- Docker/Render-ready structure

## What Day 1 implements

- FastAPI project structure
- API versioning under `/api/v1`
- Health/status endpoints
- Supabase PostgreSQL connection support
- SQLAlchemy ORM setup
- Alembic migration setup
- Initial identity tables:
  - `users`
  - `agent_profiles`
  - `admin_profiles`
- Standard API response format
- Global exception handlers
- CORS configuration
- Environment variable configuration
- Dockerfile
- Render deployment blueprint

## What Day 1 does not implement yet

- Registration/login
- JWT auth
- Paystack integration
- Property CRUD
- Supabase Storage upload
- Chat/WebSocket logic
- Admin workflows

Those are for later sprint days.

## Local setup

### 1. Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows PowerShell
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set your Supabase Postgres connection string:

```env
DATABASE_URL=postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres?sslmode=require
```

The code automatically converts `postgresql://` or `postgres://` to the SQLAlchemy Psycopg driver format.

### 4. Run migrations

```bash
alembic upgrade head
```

### 5. Start server

```bash
uvicorn app.main:app --reload
```

Open:

```txt
http://localhost:8000/docs
```

## Main endpoints

```txt
GET /
GET /health
GET /api/v1/status
GET /api/v1/health
```

## Day 1 acceptance checks

```bash
python scripts/check_db.py
pytest
```

`python scripts/check_db.py` requires `DATABASE_URL` to be configured.

## Recommended Supabase notes

Use Supabase as the managed PostgreSQL database. The mobile app should not directly write business data to Supabase. The correct flow is:

```txt
Mobile App → FastAPI → Supabase PostgreSQL
```

FastAPI remains the control layer for auth, payments, permissions, agent approval, admin actions, property rules, and future chat authorization.
