# ProHub v0.8 Deployment Instructions

## What changed

This build adds admin-granted/revoked agent access, agent step-down, geographic multi-agent group chats, listing sharing in groups, stricter public-listing access filtering, and a compatibility fix for email OTP request naming.

## Required manual steps

### 1. Back up the production database

Take a Supabase/PostgreSQL backup before applying the migration.

### 2. Preserve your existing `.env`

The distributed zip intentionally does not contain the uploaded `.env` file because it may contain production secrets. Keep the `.env` already configured on Render/your deployment platform.

No new environment variable is required for these features. Existing Paystack, Supabase, JWT, Resend, subscription, and Noxer-contact variables remain in use.

### 3. Install/update dependencies

```bash
pip install -r requirements.txt
```

### 4. Confirm migration graph

```bash
alembic heads
```

Expected head:

```text
0006_agent_access_and_group_chats
```

The package includes a compatibility bridge for the duplicate historical `0004` branch that existed in the uploaded code.

### 5. Apply database migration

```bash
alembic upgrade head
```

The migration adds geographic group-chat fields, listing references on messages, indexes, and also reconciles schema differences if the historical alternate `0004_identity_subscription_chat_upgrade` revision had already been deployed.

### 6. Restart/redeploy the API

For Render, deploy the updated repository/zip using the same service. A second service is not required.

### 7. Smoke tests after deployment

Check:

```text
GET /health
GET /api/v1/status
```

Then test these flows with test accounts:

1. Admin approves an agent with `allow_override=true`.
2. Confirm response shows `subscription_status=ADMIN_GRANTED` and a future expiry about 12 months away.
3. Agent creates/updates a property and opens chat successfully.
4. Admin calls `/revoke-access`.
5. Confirm that agent property-write endpoints and chat return `403`.
6. Agent completes a new Paystack subscription; confirm access becomes `ACTIVE` again.
7. Admin calls `/step-down`; confirm status becomes `PENDING` and access `REVOKED`.
8. Active agent creates a geographic group, another active agent joins it, and both use the existing WebSocket endpoint.
9. Share an existing listing with `/messages/listing` and confirm the location check rejects a property outside the group geography.

## Mobile-team changes

The mobile app should treat both `ACTIVE` and `ADMIN_GRANTED` as valid agent access when `subscription_expires_at` is still in the future. `REVOKED` must show a subscription-required/access-revoked state.

Group chat uses the same WebSocket implementation already integrated for private chat. The new REST endpoints are documented in `docs/AGENT_ACCESS_AND_GROUP_CHAT_API.md`.

## Validation performed before packaging

- Python bytecode compilation: passed.
- SQLAlchemy mapper configuration: passed.
- FastAPI OpenAPI generation: passed.
- Alembic graph: one head (`0006_agent_access_and_group_chats`).
- Automated tests: passed.

Live Supabase/Paystack/Resend calls are not executed locally because production credentials and external network services are required. Run the smoke tests above after deployment.
