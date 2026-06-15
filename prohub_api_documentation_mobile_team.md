# ProHub Backend API Documentation for Mobile Frontend Team

Version: Current async FastAPI build with authentication, agent workflow, Paystack payments, property listings, Supabase Storage media, admin moderation, persistent chat, and WebSocket chat.

This document is written for the mobile frontend team. It explains what has been built, how to call each endpoint, when to use each endpoint, what payloads to send, and how the main user flows should work.

---

## 1. System Overview

The mobile app must communicate with the FastAPI backend only.

Correct architecture:

```txt
Mobile App → FastAPI Backend → Supabase PostgreSQL / Supabase Storage / Paystack
```

Do not write directly to Supabase from the mobile app. The backend controls authentication, authorization, agent approval, Paystack verification, property ownership, media validation, chat permissions, and admin actions.

Current backend modules implemented:

```txt
1. Core health/status APIs
2. Authentication and JWT session management
3. Password reset foundation
4. Agent profile and status workflow
5. Admin agent approval/rejection/disable/enable
6. Property CRUD
7. Supabase Storage media upload for property images
8. Property search/filtering/pagination
9. Admin property moderation
10. Paystack agent-verification payment
11. Transaction history
12. Persistent private chat
13. Text/image/video chat messages
14. WebSocket real-time chat
15. Admin activity logs
```

---

## 2. Base URL and API Prefix

Local development base URL:

```txt
http://localhost:8000
```

Production base URL:

```txt
https://<your-backend-domain>
```

API prefix:

```txt
/api/v1
```

Swagger/OpenAPI documentation:

```txt
GET /docs
```

Root health check:

```txt
GET /health
```

---

## 3. Standard Response Format

Most successful responses follow this structure:

```json
{
  "success": true,
  "message": "Human-readable success message",
  "data": {}
}
```

Paginated responses follow this structure:

```json
{
  "success": true,
  "message": "Records retrieved",
  "data": {
    "items": [],
    "meta": {
      "page": 1,
      "limit": 20,
      "total": 0
    }
  }
}
```

Validation error response:

```json
{
  "success": false,
  "message": "Validation error.",
  "data": null,
  "errors": [
    {
      "type": "missing",
      "loc": ["body", "email"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

Application error response may appear as:

```json
{
  "success": false,
  "message": "HTTP error",
  "data": null,
  "errors": {
    "message": "You do not have permission to perform this action",
    "details": null
  }
}
```

Mobile should use HTTP status code first, then read `message` or `errors.message` for display/debugging.

---

## 4. Authentication Rules

Protected endpoints require this header:

```http
Authorization: Bearer <access_token>
```

Token handling rules for mobile:

```txt
1. Store access_token and refresh_token securely.
2. Do not store tokens in plain AsyncStorage without encryption.
3. If a protected request returns 401, call POST /api/v1/auth/refresh.
4. If refresh succeeds, replace both tokens and retry the failed request.
5. If refresh fails, clear local tokens and redirect to login.
```

Recommended secure storage:

```txt
iOS: Keychain
Android: Keystore / EncryptedSharedPreferences
React Native: expo-secure-store or react-native-keychain
Flutter: flutter_secure_storage
```

---

## 5. Roles, Statuses, and Enums

### User roles

```txt
USER
AGENT
ADMIN
SUPER_ADMIN
```

### Agent statuses

```txt
PENDING   → agent profile created but payment not verified
PAID      → Paystack payment confirmed, awaiting admin approval
APPROVED  → agent approved and allowed to post properties
REJECTED  → agent rejected by admin
DISABLED  → agent blocked by admin
```

### Property categories

```txt
LAND
HOUSE
APARTMENT
COMMERCIAL
OFFICE
SHOP
WAREHOUSE
```

### Listing types

```txt
SALE
RENT
SHORTLET
```

### Property statuses

```txt
AVAILABLE
SOLD
RENTED
PENDING
HIDDEN
```

### Property sort values

```txt
newest
oldest
price_asc
price_desc
```

### Media types

```txt
IMAGE
VIDEO
```

### Transaction statuses

```txt
PENDING
SUCCESS
FAILED
ABANDONED
ONGOING
CANCELLED
```

### Message types

```txt
TEXT
IMAGE
VIDEO
SYSTEM
```

---

## 6. Core APIs

### 6.1 GET `/health`

Purpose: Root health check for server uptime.

Auth: No.

Use when: Testing server availability or configuring deployment health checks.

Success response:

```json
{
  "success": true,
  "message": "API is running",
  "data": {
    "status": "ok"
  }
}
```

---

### 6.2 GET `/api/v1/health`

Purpose: Versioned API health check.

Auth: No.

Success response:

```json
{
  "success": true,
  "message": "API is running",
  "data": {
    "status": "ok"
  }
}
```

---

### 6.3 GET `/api/v1/status`

Purpose: Checks API and database availability.

Auth: No.

Success response:

```json
{
  "success": true,
  "message": "Service status",
  "data": {
    "api": "ok",
    "database": "ok"
  }
}
```

---

## 7. Authentication APIs

### 7.1 POST `/api/v1/auth/register`

Purpose: Register a new normal user account.

Auth: No.

When to use: User creates an account before browsing, saving, chatting, or becoming an agent.

Request body:

```json
{
  "email": "user@example.com",
  "full_name": "John Doe",
  "phone": "+2348012345678",
  "password": "StrongPassword123!"
}
```

Field rules:

```txt
email: required, valid email
full_name: required, 2–150 characters
phone: optional, max 32 characters
password: required, 8–128 characters
```

Success: `201 Created`

Success response:

```json
{
  "success": true,
  "message": "Registration successful",
  "data": {
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "phone": "+2348012345678",
      "full_name": "John Doe",
      "role": "USER",
      "is_active": true,
      "is_email_verified": false,
      "created_at": "2026-06-15T10:00:00Z",
      "updated_at": "2026-06-15T10:00:00Z"
    },
    "tokens": {
      "access_token": "jwt-access-token",
      "refresh_token": "jwt-refresh-token",
      "token_type": "bearer",
      "expires_at": "2026-06-15T10:30:00Z"
    }
  }
}
```

Mobile action:

```txt
1. Save access_token and refresh_token securely.
2. Save user object in app state.
3. Route user to authenticated area.
```

Common errors:

```txt
409: email or phone already exists
422: invalid request body
```

---

### 7.2 POST `/api/v1/auth/login`

Purpose: Authenticate an existing user and issue new access/refresh tokens.

Auth: No.

Request body:

```json
{
  "email": "user@example.com",
  "password": "StrongPassword123!"
}
```

Success response:

```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "phone": "+2348012345678",
      "full_name": "John Doe",
      "role": "USER",
      "is_active": true,
      "is_email_verified": false,
      "created_at": "2026-06-15T10:00:00Z",
      "updated_at": "2026-06-15T10:00:00Z"
    },
    "tokens": {
      "access_token": "jwt-access-token",
      "refresh_token": "jwt-refresh-token",
      "token_type": "bearer",
      "expires_at": "2026-06-15T10:30:00Z"
    }
  }
}
```

Mobile action:

```txt
1. Save both tokens securely.
2. Call /api/v1/auth/me after app restart to restore session.
```

Common errors:

```txt
401: invalid credentials
403: disabled/inactive account
422: invalid request body
```

---

### 7.3 POST `/api/v1/auth/refresh`

Purpose: Exchange a valid refresh token for a new access token and new refresh token.

Auth: No.

Request body:

```json
{
  "refresh_token": "current-refresh-token"
}
```

Success response:

```json
{
  "success": true,
  "message": "Token refreshed",
  "data": {
    "access_token": "new-jwt-access-token",
    "refresh_token": "new-jwt-refresh-token",
    "token_type": "bearer",
    "expires_at": "2026-06-15T11:00:00Z"
  }
}
```

Mobile action:

```txt
Replace both the old access token and old refresh token. Refresh tokens are rotated.
```

Common errors:

```txt
401: refresh token invalid, expired, reused, or revoked
422: invalid payload
```

---

### 7.4 POST `/api/v1/auth/logout`

Purpose: Revoke the refresh token.

Auth: No.

Request body:

```json
{
  "refresh_token": "current-refresh-token"
}
```

Success response:

```json
{
  "success": true,
  "message": "Logout successful",
  "data": {
    "logged_out": true
  }
}
```

Mobile action:

```txt
1. Call logout.
2. Clear local access token, refresh token, and cached user data.
3. Navigate to login/welcome screen.
```

If logout request fails due to network issues, still clear local tokens.

---

### 7.5 GET `/api/v1/auth/me`

Purpose: Fetch the currently authenticated user.

Auth: Yes.

Header:

```http
Authorization: Bearer <access_token>
```

Success response:

```json
{
  "success": true,
  "message": "Current user",
  "data": {
    "id": "uuid",
    "email": "user@example.com",
    "phone": "+2348012345678",
    "full_name": "John Doe",
    "role": "AGENT",
    "is_active": true,
    "is_email_verified": false,
    "created_at": "2026-06-15T10:00:00Z",
    "updated_at": "2026-06-15T10:00:00Z",
    "agent_status": "APPROVED",
    "is_super_admin": false
  }
}
```

Use for:

```txt
1. Session restore on app launch.
2. Role-based navigation.
3. Agent onboarding status display.
4. Admin dashboard access gating.
```

---

### 7.6 POST `/api/v1/auth/request-reset`

Purpose: Start password reset flow.

Auth: No.

Request body:

```json
{
  "email": "user@example.com"
}
```

Success response in development:

```json
{
  "success": true,
  "message": "Password reset requested",
  "data": {
    "message": "If this email exists, a reset code has been generated.",
    "debug_reset_token": "reset-token-for-dev",
    "debug_otp_code": "123456"
  }
}
```

Important production note:

```txt
Email/SMS delivery is not implemented. In production, debug_reset_token and debug_otp_code must not be returned to the mobile app. The backend needs an email/SMS provider to deliver reset codes.
```

---

### 7.7 POST `/api/v1/auth/verify-reset`

Purpose: Verify reset token and OTP before allowing password change.

Auth: No.

Request body:

```json
{
  "reset_token": "reset-token",
  "otp_code": "123456"
}
```

Success response:

```json
{
  "success": true,
  "message": "Reset token verified",
  "data": {
    "valid": true
  }
}
```

---

### 7.8 POST `/api/v1/auth/reset-password`

Purpose: Set a new password after token/OTP verification.

Auth: No.

Request body:

```json
{
  "reset_token": "reset-token",
  "otp_code": "123456",
  "new_password": "NewStrongPassword123!"
}
```

Success response:

```json
{
  "success": true,
  "message": "Password reset successful",
  "data": {
    "reset": true
  }
}
```

Mobile action:

```txt
After success, route user to login and clear reset token/OTP from local state.
```

---

## 8. Agent APIs

### 8.1 POST `/api/v1/agents/me`

Purpose: Convert the current authenticated user into an agent by creating an agent profile.

Auth: Yes.

When to use: User taps “Become an Agent” and submits business information.

Request body:

```json
{
  "business_name": "Prime Lands Realty",
  "business_phone": "+2348012345678",
  "business_email": "agency@example.com",
  "license_number": "ABC-12345",
  "address": "12 Example Street",
  "city": "Ikeja",
  "state": "Lagos",
  "country": "Nigeria"
}
```

Success: `201 Created`

Success response:

```json
{
  "success": true,
  "message": "Agent profile created",
  "data": {
    "id": "agent-profile-uuid",
    "user_id": "user-uuid",
    "business_name": "Prime Lands Realty",
    "business_phone": "+2348012345678",
    "business_email": "agency@example.com",
    "license_number": "ABC-12345",
    "address": "12 Example Street",
    "city": "Ikeja",
    "state": "Lagos",
    "country": "Nigeria",
    "status": "PENDING",
    "previous_status": null,
    "status_note": null,
    "approved_at": null,
    "rejected_at": null,
    "disabled_at": null,
    "created_at": "2026-06-15T10:00:00Z",
    "updated_at": "2026-06-15T10:00:00Z"
  }
}
```

Important:

```txt
A new agent starts as PENDING. They must pay through Paystack, then admin must approve them before they can post properties.
```

---

### 8.2 GET `/api/v1/agents/me`

Purpose: Get the current user’s agent profile.

Auth: Yes.

Use when: Displaying agent onboarding/payment/approval status.

Success response:

```json
{
  "success": true,
  "message": "Agent profile",
  "data": {
    "id": "agent-profile-uuid",
    "user_id": "user-uuid",
    "business_name": "Prime Lands Realty",
    "status": "PAID",
    "status_note": "Agent verification payment confirmed via Paystack. Awaiting admin approval.",
    "approved_at": null,
    "rejected_at": null,
    "disabled_at": null,
    "created_at": "2026-06-15T10:00:00Z",
    "updated_at": "2026-06-15T10:30:00Z"
  }
}
```

---

### 8.3 PATCH `/api/v1/agents/me`

Purpose: Update the authenticated agent’s business details.

Auth: Yes.

Request body: send only the changed fields.

```json
{
  "business_name": "Prime Lands and Homes",
  "business_phone": "+2348099999999",
  "address": "25 Updated Street",
  "city": "Lekki",
  "state": "Lagos"
}
```

Success response: returns updated agent profile.

---

### 8.4 GET `/api/v1/agents/me/properties`

Purpose: List properties owned by the authenticated approved agent.

Auth: Yes. Requires agent status `APPROVED`.

Query params:

```txt
page: integer, default 1
limit: integer, default 20, max 100
```

Example:

```http
GET /api/v1/agents/me/properties?page=1&limit=20
```

Success response:

```json
{
  "success": true,
  "message": "Agent properties retrieved",
  "data": {
    "items": [],
    "meta": {
      "page": 1,
      "limit": 20,
      "total": 0
    }
  }
}
```

---

## 9. Paystack Payment APIs

The Paystack payment module is for agent verification fee payment.

Payment flow:

```txt
Agent creates profile → Agent status PENDING
Agent initializes payment → transaction PENDING
Mobile opens Paystack authorization_url
Payment succeeds → backend verifies payment
Transaction SUCCESS → Agent status PAID
Admin approves agent → Agent status APPROVED
Agent can create properties
```

Never mark an agent as paid or approved from the mobile app. The backend must verify payment through Paystack.

---

### 9.1 POST `/api/v1/payments/initialize`

Purpose: Initialize Paystack payment for agent verification fee.

Auth: Yes. User must be an `AGENT`.

When to use: Agent taps “Pay verification fee”.

Request body:

```json
{
  "callback_url": "https://your-mobile-or-web-callback-url.com/payment-result"
}
```

`callback_url` is optional. If omitted, backend uses `PAYSTACK_CALLBACK_URL` from server environment.

Success: `201 Created`

Success response:

```json
{
  "success": true,
  "message": "Payment initialized",
  "data": {
    "reference": "PROHUB_AGT_ABC123...",
    "amount": "10000.00",
    "currency": "NGN",
    "authorization_url": "https://checkout.paystack.com/...",
    "access_code": "paystack-access-code",
    "public_key": "pk_test_or_live_xxxxx"
  }
}
```

Mobile action:

```txt
1. Open authorization_url in WebView, browser, or Paystack-supported payment screen.
2. Keep reference locally for verification.
3. After payment redirect/callback, call GET /api/v1/payments/verify/{reference}.
```

Backend rules:

```txt
1. Only AGENT accounts can initialize payment.
2. APPROVED agents cannot pay again.
3. PAID agents cannot pay again; they are awaiting admin approval.
4. DISABLED agents cannot pay.
5. If a pending transaction already has an authorization_url, backend returns it instead of creating duplicate active payments.
```

Common errors:

```txt
400: verification fee not configured, already paid/approved
403: not an agent or disabled agent
422: invalid callback_url
```

---

### 9.2 GET `/api/v1/payments/verify/{reference}`

Purpose: Verify Paystack transaction after checkout.

Auth: Yes. Transaction must belong to the current user.

When to use: After Paystack returns to app or user finishes checkout.

Example:

```http
GET /api/v1/payments/verify/PROHUB_AGT_ABC123
```

Success response:

```json
{
  "success": true,
  "message": "Payment verified",
  "data": {
    "transaction": {
      "id": "transaction-uuid",
      "user_id": "user-uuid",
      "agent_id": "agent-profile-uuid",
      "provider": "PAYSTACK",
      "payment_type": "AGENT_VERIFICATION",
      "reference": "PROHUB_AGT_ABC123",
      "amount": "10000.00",
      "currency": "NGN",
      "status": "SUCCESS",
      "authorization_url": "https://checkout.paystack.com/...",
      "access_code": "access-code",
      "paid_at": "2026-06-15T10:40:00Z",
      "verified_at": "2026-06-15T10:41:00Z",
      "failure_reason": null,
      "created_at": "2026-06-15T10:30:00Z",
      "updated_at": "2026-06-15T10:41:00Z"
    },
    "agent_status": "PAID"
  }
}
```

Mobile action:

```txt
1. If transaction.status == SUCCESS and agent_status == PAID, show “Payment received. Awaiting admin approval.”
2. Refresh /api/v1/agents/me.
3. Do not show property creation until agent_status == APPROVED.
```

Common errors:

```txt
400: amount mismatch, currency mismatch, unsupported Paystack status
403: user tries to verify another user’s transaction
404: transaction not found
```

---

### 9.3 POST `/api/v1/payments/webhook`

Purpose: Receive Paystack webhook events.

Auth: No JWT. Uses Paystack signature header.

Who uses this: Paystack server only. The mobile app must not call this endpoint.

Headers:

```http
x-paystack-signature: <signature>
```

Success response:

```json
{
  "success": true,
  "message": "Webhook processed",
  "data": {
    "processed": true
  }
}
```

Backend behavior:

```txt
1. Reads raw body.
2. Verifies x-paystack-signature.
3. Processes charge.success event.
4. Finds local transaction by reference.
5. Confirms amount and currency.
6. Marks transaction SUCCESS.
7. Moves agent from PENDING/REJECTED to PAID.
8. Ignores duplicate successful events safely.
```

---

### 9.4 GET `/api/v1/payments/me`

Purpose: List current user’s transactions.

Auth: Yes.

Query params:

```txt
page: integer, default 1
limit: integer, default 20, max 100
```

Example:

```http
GET /api/v1/payments/me?page=1&limit=20
```

Success response:

```json
{
  "success": true,
  "message": "Payments retrieved",
  "data": {
    "items": [
      {
        "id": "transaction-uuid",
        "user_id": "user-uuid",
        "agent_id": "agent-profile-uuid",
        "provider": "PAYSTACK",
        "payment_type": "AGENT_VERIFICATION",
        "reference": "PROHUB_AGT_ABC123",
        "amount": "10000.00",
        "currency": "NGN",
        "status": "SUCCESS",
        "paid_at": "2026-06-15T10:40:00Z",
        "verified_at": "2026-06-15T10:41:00Z",
        "failure_reason": null,
        "created_at": "2026-06-15T10:30:00Z",
        "updated_at": "2026-06-15T10:41:00Z"
      }
    ],
    "meta": {
      "page": 1,
      "limit": 20,
      "total": 1
    }
  }
}
```

---

## 10. Property APIs

### Property creation permission rule

Only authenticated agents with `agent_status == APPROVED` can create, update, delete, or upload media for properties.

Public users can list, search, and view public properties.

---

### 10.1 POST `/api/v1/properties`

Purpose: Create a new property listing.

Auth: Yes. Requires approved agent.

Request body:

```json
{
  "title": "Land for Sale in Lekki",
  "description": "A well-positioned dry land suitable for residential development.",
  "price": "15000000.00",
  "currency": "NGN",
  "country": "Nigeria",
  "state": "Lagos",
  "local_government": "Eti-Osa",
  "community": "Lekki Phase 1",
  "address_details": "Near Admiralty Way",
  "category": "LAND",
  "listing_type": "SALE",
  "status": "AVAILABLE",
  "is_published": true
}
```

Success: `201 Created`

Success response:

```json
{
  "success": true,
  "message": "Property created",
  "data": {
    "id": "property-uuid",
    "agent_id": "agent-profile-uuid",
    "title": "Land for Sale in Lekki",
    "description": "A well-positioned dry land suitable for residential development.",
    "price": "15000000.00",
    "currency": "NGN",
    "country": "Nigeria",
    "state": "Lagos",
    "local_government": "Eti-Osa",
    "community": "Lekki Phase 1",
    "address_details": "Near Admiralty Way",
    "category": "LAND",
    "listing_type": "SALE",
    "status": "AVAILABLE",
    "is_published": true,
    "deleted_at": null,
    "created_at": "2026-06-15T10:00:00Z",
    "updated_at": "2026-06-15T10:00:00Z",
    "media": [],
    "agent": {
      "id": "agent-profile-uuid",
      "business_name": "Prime Lands Realty",
      "business_phone": "+2348012345678",
      "business_email": "agency@example.com",
      "city": "Ikeja",
      "state": "Lagos",
      "country": "Nigeria",
      "status": "APPROVED"
    }
  }
}
```

---

### 10.2 GET `/api/v1/properties`

Purpose: List public visible properties.

Auth: No.

Query params:

```txt
page: default 1
limit: default 20, max 100
```

Example:

```http
GET /api/v1/properties?page=1&limit=20
```

Success response: paginated list of `PropertyResponse`.

Note:

```txt
Use /api/v1/properties/search for filters and keyword search.
```

---

### 10.3 GET `/api/v1/properties/search`

Purpose: Search and filter public visible properties.

Auth: No.

Query params:

```txt
q: keyword; searches title, description, location fields
country
state
local_government
community
min_price
max_price
category: LAND | HOUSE | APARTMENT | COMMERCIAL | OFFICE | SHOP | WAREHOUSE
listing_type: SALE | RENT | SHORTLET
status: AVAILABLE | SOLD | RENTED | PENDING | HIDDEN
sort: newest | oldest | price_asc | price_desc; default newest
page: default 1
limit: default 20, max 100
```

Example:

```http
GET /api/v1/properties/search?q=lekki&state=Lagos&category=LAND&min_price=5000000&max_price=30000000&sort=price_asc&page=1&limit=20
```

Success response: paginated list of `PropertyResponse`.

Mobile usage:

```txt
Use this endpoint for property discovery screen, category browsing, location filters, and search bar.
```

---

### 10.4 GET `/api/v1/properties/{property_id}`

Purpose: Get one public property detail.

Auth: No.

Example:

```http
GET /api/v1/properties/property-uuid
```

Success response: one `PropertyResponse`.

Use when: User opens property detail screen.

---

### 10.5 PATCH `/api/v1/properties/{property_id}`

Purpose: Update property owned by authenticated approved agent.

Auth: Yes. Requires approved agent and ownership of the property.

Request body: send only changed fields.

```json
{
  "price": "14500000.00",
  "status": "AVAILABLE",
  "is_published": true
}
```

Success response: updated `PropertyResponse`.

Common errors:

```txt
403: not approved agent or not owner
404: property not found
422: invalid body
```

---

### 10.6 DELETE `/api/v1/properties/{property_id}`

Purpose: Soft-delete authenticated agent’s own property.

Auth: Yes. Requires approved agent and ownership.

Success response:

```json
{
  "success": true,
  "message": "Property deleted",
  "data": {
    "deleted": true
  }
}
```

Note: This is a soft delete. The database record remains but public users no longer see it.

---

### 10.7 POST `/api/v1/properties/{property_id}/media`

Purpose: Upload an image for a property.

Auth: Yes. Requires approved agent and ownership.

Content type: `multipart/form-data`

Path param:

```txt
property_id: UUID
```

Query param:

```txt
position: integer, default 0
```

Form field:

```txt
file: image file
```

Supported files:

```txt
image/jpeg
image/png
image/webp
```

Maximum property image size:

```txt
5 MB
```

Maximum property images per property:

```txt
10
```

Example form:

```txt
POST /api/v1/properties/{property_id}/media?position=0
Authorization: Bearer <agent-access-token>
Content-Type: multipart/form-data
file=<image-file>
```

Success response:

```json
{
  "success": true,
  "message": "Property image uploaded",
  "data": {
    "id": "media-uuid",
    "property_id": "property-uuid",
    "file_url": "https://.../storage/v1/object/public/property-media/properties/property-uuid/file.webp",
    "storage_path": "properties/property-uuid/file.webp",
    "media_type": "IMAGE",
    "content_type": "image/webp",
    "file_size_bytes": 204800,
    "position": 0,
    "created_at": "2026-06-15T10:00:00Z",
    "updated_at": "2026-06-15T10:00:00Z"
  }
}
```

---

### 10.8 DELETE `/api/v1/properties/{property_id}/media/{media_id}`

Purpose: Delete property image from Supabase Storage and database.

Auth: Yes. Requires approved agent and ownership.

Success response:

```json
{
  "success": true,
  "message": "Property image deleted",
  "data": {
    "deleted": true
  }
}
```

---

## 11. Chat APIs

Chat is private buyer-agent messaging with persistence and WebSocket broadcasting.

Chat rules:

```txt
1. Any authenticated user can start a private chat with an APPROVED agent.
2. User cannot start a chat with themselves.
3. If property_id is provided, property must exist publicly and belong to the selected agent.
4. Only chat participants can view chat, list messages, send messages, upload chat media, mark read, or connect to WebSocket.
5. Text messages can be sent through REST or WebSocket.
6. Image/video messages are uploaded through REST, then broadcast over WebSocket.
```

---

### 11.1 POST `/api/v1/chats`

Purpose: Start or retrieve a private chat with an approved agent.

Auth: Yes.

Request body:

```json
{
  "agent_id": "agent-profile-uuid",
  "property_id": "property-uuid",
  "initial_message": "Hello, I am interested in this property."
}
```

Field rules:

```txt
agent_id: required, agent profile UUID
property_id: optional, property UUID
initial_message: optional, 1–5000 chars
```

Success: `201 Created`

Success response:

```json
{
  "success": true,
  "message": "Chat ready",
  "data": {
    "id": "chat-uuid",
    "chat_type": "PRIVATE",
    "property_id": "property-uuid",
    "created_by_id": "user-uuid",
    "title": "Land for Sale in Lekki",
    "last_message_id": "message-uuid",
    "last_message_at": "2026-06-15T10:00:00Z",
    "created_at": "2026-06-15T10:00:00Z",
    "updated_at": "2026-06-15T10:00:00Z",
    "participants": [
      {
        "id": "participant-uuid",
        "chat_id": "chat-uuid",
        "user_id": "user-uuid",
        "role": "MEMBER",
        "joined_at": "2026-06-15T10:00:00Z",
        "left_at": null,
        "last_read_at": null,
        "user": null
      }
    ],
    "property": {
      "id": "property-uuid",
      "title": "Land for Sale in Lekki",
      "state": "Lagos",
      "community": "Lekki Phase 1"
    }
  }
}
```

Mobile action:

```txt
1. Call when user taps “Message Agent” on property detail.
2. Save returned chat.id.
3. Navigate to chat screen.
4. Open WebSocket for live messages.
```

---

### 11.2 GET `/api/v1/chats`

Purpose: List current user’s chat inbox.

Auth: Yes.

Query params:

```txt
page: default 1
limit: default 20, max 100
```

Success response:

```json
{
  "success": true,
  "message": "Chats retrieved",
  "data": {
    "items": [
      {
        "id": "chat-uuid",
        "chat_type": "PRIVATE",
        "property_id": "property-uuid",
        "title": "Land for Sale in Lekki",
        "last_message_at": "2026-06-15T10:00:00Z",
        "created_at": "2026-06-15T09:50:00Z",
        "updated_at": "2026-06-15T10:00:00Z",
        "participants": [],
        "property": {
          "id": "property-uuid",
          "title": "Land for Sale in Lekki",
          "state": "Lagos",
          "community": "Lekki Phase 1"
        },
        "last_message": {
          "id": "message-uuid",
          "chat_id": "chat-uuid",
          "sender_id": "user-uuid",
          "content": "Hello, is this still available?",
          "message_type": "TEXT",
          "media_url": null,
          "created_at": "2026-06-15T10:00:00Z",
          "updated_at": "2026-06-15T10:00:00Z"
        },
        "unread_count": 2
      }
    ],
    "meta": {
      "page": 1,
      "limit": 20,
      "total": 1
    }
  }
}
```

Mobile usage:

```txt
Use for chat inbox/conversation list screen.
```

---

### 11.3 GET `/api/v1/chats/{chat_id}`

Purpose: Get chat details.

Auth: Yes. User must be participant.

Success response: `ChatResponse`.

---

### 11.4 GET `/api/v1/chats/{chat_id}/messages`

Purpose: Load chat message history.

Auth: Yes. User must be participant.

Query params:

```txt
page: default 1
limit: default 50, max 100
```

Success response:

```json
{
  "success": true,
  "message": "Messages retrieved",
  "data": {
    "items": [
      {
        "id": "message-uuid",
        "chat_id": "chat-uuid",
        "sender_id": "user-uuid",
        "content": "Hello, is this property still available?",
        "message_type": "TEXT",
        "media_url": null,
        "media_path": null,
        "media_content_type": null,
        "media_size_bytes": null,
        "read_at": null,
        "deleted_at": null,
        "created_at": "2026-06-15T10:00:00Z",
        "updated_at": "2026-06-15T10:00:00Z",
        "sender": {
          "id": "user-uuid",
          "email": "user@example.com",
          "phone": "+2348012345678",
          "full_name": "John Doe",
          "role": "USER",
          "is_active": true,
          "is_email_verified": false,
          "created_at": "2026-06-15T09:00:00Z",
          "updated_at": "2026-06-15T09:00:00Z"
        }
      }
    ],
    "meta": {
      "page": 1,
      "limit": 50,
      "total": 1
    }
  }
}
```

---

### 11.5 POST `/api/v1/chats/{chat_id}/messages`

Purpose: Send a text message through REST fallback.

Auth: Yes. User must be participant.

Request body:

```json
{
  "content": "Is this property still available?",
  "message_type": "TEXT"
}
```

Important:

```txt
Only TEXT is allowed here. Use /messages/media for IMAGE or VIDEO.
```

Success: `201 Created`

Success response: `MessageResponse`.

Mobile usage:

```txt
Use this as fallback when WebSocket is disconnected or unreliable.
```

---

### 11.6 POST `/api/v1/chats/{chat_id}/messages/media`

Purpose: Send image or video message.

Auth: Yes. User must be participant.

Content type: `multipart/form-data`

Form fields:

```txt
file: required, image/video file
content: optional text caption, max 5000 chars
```

Supported image types:

```txt
image/jpeg
image/png
image/webp
```

Supported video types:

```txt
video/mp4
video/webm
video/quicktime
```

Configured limits:

```txt
MAX_CHAT_IMAGE_SIZE_MB: default 5 MB
MAX_CHAT_VIDEO_SIZE_MB: default 50 MB
```

Example:

```txt
POST /api/v1/chats/{chat_id}/messages/media
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
file=<image-or-video-file>
content="See attached video"
```

Success response for image:

```json
{
  "success": true,
  "message": "Media message sent",
  "data": {
    "id": "message-uuid",
    "chat_id": "chat-uuid",
    "sender_id": "user-uuid",
    "content": "See attached image",
    "message_type": "IMAGE",
    "media_url": "https://.../storage/v1/object/public/property-media/chats/chat-uuid/file.webp",
    "media_path": "chats/chat-uuid/file.webp",
    "media_content_type": "image/webp",
    "media_size_bytes": 204800,
    "read_at": null,
    "deleted_at": null,
    "created_at": "2026-06-15T10:00:00Z",
    "updated_at": "2026-06-15T10:00:00Z"
  }
}
```

Important:

```txt
Do not send binary files through WebSocket. Upload media through REST. The backend broadcasts the saved media message over WebSocket after successful upload.
```

---

### 11.7 PATCH `/api/v1/chats/{chat_id}/read`

Purpose: Mark chat as read for current user.

Auth: Yes. User must be participant.

Success response:

```json
{
  "success": true,
  "message": "Chat marked as read",
  "data": {
    "chat_id": "chat-uuid",
    "unread_count": 0,
    "last_read_at": "2026-06-15T10:05:00Z"
  }
}
```

Mobile usage:

```txt
Call when user opens chat screen or after messages are rendered.
```

---

## 12. WebSocket Chat API

### 12.1 WebSocket `/api/v1/ws/chats/{chat_id}?token=<access_token>`

Purpose: Real-time chat for text message delivery and message broadcasts.

Connection URL:

```txt
ws://localhost:8000/api/v1/ws/chats/{chat_id}?token=<access_token>
```

Production:

```txt
wss://<backend-domain>/api/v1/ws/chats/{chat_id}?token=<access_token>
```

Auth:

```txt
Pass access token as query parameter named token.
```

Connection rules:

```txt
1. Token must be valid access token.
2. User must be active.
3. User must be participant in chat.
4. Otherwise socket closes with policy violation.
```

---

### Client event: send text message

Client sends:

```json
{
  "type": "message.send",
  "data": {
    "content": "Hello, is this property still available?"
  }
}
```

Server broadcasts to chat participants:

```json
{
  "type": "message.created",
  "data": {
    "id": "message-uuid",
    "chat_id": "chat-uuid",
    "sender_id": "user-uuid",
    "content": "Hello, is this property still available?",
    "message_type": "TEXT",
    "media_url": null,
    "media_path": null,
    "media_content_type": null,
    "media_size_bytes": null,
    "read_at": null,
    "deleted_at": null,
    "created_at": "2026-06-15T10:00:00Z",
    "updated_at": "2026-06-15T10:00:00Z"
  }
}
```

---

### Client event: mark read

Client sends:

```json
{
  "type": "chat.read",
  "data": {}
}
```

Server responds to sender:

```json
{
  "type": "chat.read",
  "data": {
    "chat_id": "chat-uuid",
    "last_read_at": "2026-06-15T10:05:00Z",
    "unread_count": 0
  }
}
```

---

### Server error event

```json
{
  "type": "error",
  "data": {
    "message": "Unsupported event type"
  }
}
```

Mobile WebSocket rules:

```txt
1. Use REST /messages endpoint as fallback if socket is disconnected.
2. Reconnect after app resumes from background.
3. Refresh token before reconnecting if access token expired.
4. Upload images/videos through REST /messages/media only.
```

---

## 13. Admin APIs

Admin endpoints require `ADMIN` or `SUPER_ADMIN`.

---

### 13.1 GET `/api/v1/admin/agents`

Purpose: List agents for review/management.

Auth: Admin only.

Query params:

```txt
page: default 1
limit: default 20, max 100
status: PENDING | PAID | APPROVED | REJECTED | DISABLED
q: search string, max 100 chars
```

Example:

```http
GET /api/v1/admin/agents?status=PAID&page=1&limit=20
```

Success response: paginated list of `AgentAdminResponse`, including agent profile and user info.

---

### 13.2 GET `/api/v1/admin/agents/{agent_id}`

Purpose: View one agent profile.

Auth: Admin only.

Note: `agent_id` is agent profile ID, not user ID.

---

### 13.3 PATCH `/api/v1/admin/agents/{agent_id}/approve`

Purpose: Approve paid agent.

Auth: Admin only.

Request body:

```json
{
  "note": "Payment verified and business details reviewed.",
  "allow_unpaid_override": false
}
```

Rules:

```txt
By default, only PAID agents can be approved.
allow_unpaid_override should be false in production.
```

Success response: updated `AgentAdminResponse` with `status: APPROVED`.

---

### 13.4 PATCH `/api/v1/admin/agents/{agent_id}/reject`

Purpose: Reject an agent application.

Auth: Admin only.

Request body:

```json
{
  "note": "Business information could not be verified."
}
```

Success response: updated `AgentAdminResponse` with `status: REJECTED`.

---

### 13.5 PATCH `/api/v1/admin/agents/{agent_id}/disable`

Purpose: Disable an agent account.

Auth: Admin only.

Request body:

```json
{
  "note": "Disabled due to suspicious activity."
}
```

Success response: updated `AgentAdminResponse` with `status: DISABLED`.

---

### 13.6 PATCH `/api/v1/admin/agents/{agent_id}/enable`

Purpose: Re-enable a disabled agent.

Auth: Admin only.

Request body:

```json
{
  "note": "Review completed. Agent restored."
}
```

Success response: updated `AgentAdminResponse`.

---

### 13.7 GET `/api/v1/admin/properties`

Purpose: Admin list/search all properties, including hidden or optionally deleted ones.

Auth: Admin only.

Query params:

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
agent_id
include_deleted: boolean, default false
page
limit
```

Example:

```http
GET /api/v1/admin/properties?status=HIDDEN&include_deleted=false&page=1&limit=20
```

Success response: paginated list of `PropertyResponse`.

---

### 13.8 GET `/api/v1/admin/properties/{property_id}`

Purpose: Admin view one property, even if hidden/deleted depending backend query.

Auth: Admin only.

---

### 13.9 PATCH `/api/v1/admin/properties/{property_id}/hide`

Purpose: Hide a suspicious/fraudulent listing from public users.

Auth: Admin only.

Request body:

```json
{
  "note": "Suspicious listing. Hidden pending review."
}
```

Success response: updated `PropertyResponse` with `status: HIDDEN` and `is_published: false`.

---

### 13.10 PATCH `/api/v1/admin/properties/{property_id}/restore`

Purpose: Restore a hidden property.

Auth: Admin only.

Request body:

```json
{
  "note": "Review completed. Listing restored.",
  "status": "AVAILABLE",
  "is_published": true
}
```

Success response: updated `PropertyResponse`.

---

### 13.11 DELETE `/api/v1/admin/properties/{property_id}`

Purpose: Admin soft-delete a property.

Auth: Admin only.

Query param:

```txt
note: optional string, max 1000 chars
```

Example:

```http
DELETE /api/v1/admin/properties/property-uuid?note=Fraudulent%20listing
```

Success response:

```json
{
  "success": true,
  "message": "Property deleted by admin",
  "data": {
    "deleted": true
  }
}
```

---

### 13.12 GET `/api/v1/admin/transactions`

Purpose: Admin list all payment transactions.

Auth: Admin only.

Query params:

```txt
status: PENDING | SUCCESS | FAILED | ABANDONED | ONGOING | CANCELLED
page: default 1
limit: default 20, max 100
```

Example:

```http
GET /api/v1/admin/transactions?status=SUCCESS&page=1&limit=20
```

Success response: paginated list of `TransactionResponse`.

---

### 13.13 GET `/api/v1/admin/activity-logs`

Purpose: Admin audit trail for approval, moderation, payment verification, etc.

Auth: Admin only.

Query params:

```txt
page: default 1
limit: default 20, max 100
```

Success response:

```json
{
  "success": true,
  "message": "Admin activity logs retrieved",
  "data": {
    "items": [
      {
        "id": "log-uuid",
        "admin_id": "admin-user-uuid",
        "action": "AGENT_APPROVED",
        "target_type": "agent_profile",
        "target_id": "agent-profile-uuid",
        "description": "Approved agent Prime Lands Realty",
        "metadata_json": {},
        "created_at": "2026-06-15T10:00:00Z"
      }
    ],
    "meta": {
      "page": 1,
      "limit": 20,
      "total": 1
    }
  }
}
```

---

## 14. Main Mobile Integration Flows

### 14.1 Normal user flow

```txt
1. POST /auth/register or POST /auth/login
2. Store tokens securely
3. GET /auth/me on app startup
4. GET /properties/search for property discovery
5. GET /properties/{property_id} for detail page
6. POST /chats to contact agent
7. Connect WebSocket for live chat
```

---

### 14.2 Agent onboarding flow

```txt
1. User registers/logs in
2. POST /agents/me to create agent profile
3. Status becomes PENDING
4. POST /payments/initialize
5. Open Paystack authorization_url
6. GET /payments/verify/{reference}
7. If successful, status becomes PAID
8. Admin approves agent
9. Agent status becomes APPROVED
10. Agent can POST /properties
```

---

### 14.3 Property posting flow

```txt
1. Agent must be APPROVED
2. POST /properties
3. POST /properties/{property_id}/media for each image
4. GET /agents/me/properties to show agent dashboard
5. PATCH /properties/{property_id} to update
6. DELETE /properties/{property_id} to soft-delete
```

---

### 14.4 Buyer-agent chat flow

```txt
1. User opens property detail
2. User taps Message Agent
3. POST /chats with agent_id and property_id
4. GET /chats/{chat_id}/messages to load history
5. Connect WS /ws/chats/{chat_id}?token=<access_token>
6. Send text through WebSocket or REST
7. Upload image/video through REST /messages/media
8. PATCH /chats/{chat_id}/read when chat is opened
```

---

### 14.5 Token refresh flow

```txt
1. Any protected request returns 401
2. POST /auth/refresh with refresh_token
3. Save new access_token and refresh_token
4. Retry original request
5. If refresh fails, logout locally
```

---

## 15. Mobile Implementation Warnings

```txt
1. Do not store Supabase service role key in the mobile app.
2. Do not let mobile write directly to Supabase.
3. Do not trust Paystack callback alone; always call backend verify endpoint.
4. Do not show property creation UI unless agent_status == APPROVED.
5. Do not send image/video through WebSocket; use REST media upload.
6. Always handle token refresh before declaring a user logged out.
7. Always check HTTP status codes and backend success flag.
8. Treat all IDs as UUID strings.
9. Paginated endpoints always need page and limit handling.
10. In production, password reset requires email/SMS provider integration.
```

---

## 16. Manual Backend/DevOps Configuration Needed

These are not mobile tasks, but they affect mobile integration.

### Paystack `.env`

```env
PAYSTACK_PUBLIC_KEY="pk_test_or_live_xxxxx"
PAYSTACK_SECRET_KEY="sk_test_or_live_xxxxx"
PAYSTACK_WEBHOOK_SECRET=""
PAYSTACK_CURRENCY="NGN"
AGENT_VERIFICATION_FEE=10000
PAYSTACK_CALLBACK_URL="https://your-mobile-or-web-callback-url.com/payment-result"
PAYSTACK_BASE_URL="https://api.paystack.co"
```

### Supabase Storage `.env`

```env
SUPABASE_URL="https://your-project-ref.supabase.co"
SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
SUPABASE_STORAGE_BUCKET="property-media"
MAX_CHAT_IMAGE_SIZE_MB=5
MAX_CHAT_VIDEO_SIZE_MB=50
```

### Supabase bucket

Bucket name:

```txt
property-media
```

Bucket access:

```txt
Public for MVP
```

Allowed content types:

```txt
image/jpeg
image/png
image/webp
video/mp4
video/webm
video/quicktime
```

### Paystack webhook URL

```txt
https://<backend-domain>/api/v1/payments/webhook
```

---

## 17. Endpoint Summary Table

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | No | Root health check |
| GET | `/api/v1/health` | No | Versioned health check |
| GET | `/api/v1/status` | No | API/database status |
| POST | `/api/v1/auth/register` | No | Register user |
| POST | `/api/v1/auth/login` | No | Login user |
| POST | `/api/v1/auth/refresh` | No | Refresh tokens |
| POST | `/api/v1/auth/logout` | No | Revoke refresh token |
| GET | `/api/v1/auth/me` | Yes | Current user |
| POST | `/api/v1/auth/request-reset` | No | Start password reset |
| POST | `/api/v1/auth/verify-reset` | No | Verify reset OTP |
| POST | `/api/v1/auth/reset-password` | No | Set new password |
| POST | `/api/v1/agents/me` | Yes | Create agent profile |
| GET | `/api/v1/agents/me` | Yes | Get own agent profile |
| PATCH | `/api/v1/agents/me` | Yes | Update own agent profile |
| GET | `/api/v1/agents/me/properties` | Approved Agent | List own properties |
| POST | `/api/v1/payments/initialize` | Agent | Start Paystack payment |
| GET | `/api/v1/payments/verify/{reference}` | Agent | Verify Paystack payment |
| POST | `/api/v1/payments/webhook` | Paystack signature | Paystack webhook |
| GET | `/api/v1/payments/me` | Yes | My transactions |
| POST | `/api/v1/properties` | Approved Agent | Create property |
| GET | `/api/v1/properties` | No | List public properties |
| GET | `/api/v1/properties/search` | No | Search/filter properties |
| GET | `/api/v1/properties/{property_id}` | No | Public property detail |
| PATCH | `/api/v1/properties/{property_id}` | Approved Agent Owner | Update property |
| DELETE | `/api/v1/properties/{property_id}` | Approved Agent Owner | Soft-delete property |
| POST | `/api/v1/properties/{property_id}/media` | Approved Agent Owner | Upload property image |
| DELETE | `/api/v1/properties/{property_id}/media/{media_id}` | Approved Agent Owner | Delete property image |
| POST | `/api/v1/chats` | Yes | Start/get chat |
| GET | `/api/v1/chats` | Yes | List my chats |
| GET | `/api/v1/chats/{chat_id}` | Chat Participant | Get chat |
| GET | `/api/v1/chats/{chat_id}/messages` | Chat Participant | List messages |
| POST | `/api/v1/chats/{chat_id}/messages` | Chat Participant | Send text message |
| POST | `/api/v1/chats/{chat_id}/messages/media` | Chat Participant | Send image/video message |
| PATCH | `/api/v1/chats/{chat_id}/read` | Chat Participant | Mark chat read |
| WS | `/api/v1/ws/chats/{chat_id}?token=...` | Chat Participant | Realtime chat |
| GET | `/api/v1/admin/agents` | Admin | List agents |
| GET | `/api/v1/admin/agents/{agent_id}` | Admin | View agent |
| PATCH | `/api/v1/admin/agents/{agent_id}/approve` | Admin | Approve agent |
| PATCH | `/api/v1/admin/agents/{agent_id}/reject` | Admin | Reject agent |
| PATCH | `/api/v1/admin/agents/{agent_id}/disable` | Admin | Disable agent |
| PATCH | `/api/v1/admin/agents/{agent_id}/enable` | Admin | Enable agent |
| GET | `/api/v1/admin/properties` | Admin | List all properties |
| GET | `/api/v1/admin/properties/{property_id}` | Admin | View any property |
| PATCH | `/api/v1/admin/properties/{property_id}/hide` | Admin | Hide property |
| PATCH | `/api/v1/admin/properties/{property_id}/restore` | Admin | Restore property |
| DELETE | `/api/v1/admin/properties/{property_id}` | Admin | Admin soft-delete property |
| GET | `/api/v1/admin/transactions` | Admin | List all transactions |
| GET | `/api/v1/admin/activity-logs` | Admin | List admin logs |

---

## 18. Remaining Gaps / Future Work

The current backend is MVP-ready for auth, agent onboarding, payments, property listing, search, moderation, and chat. Future improvements:

```txt
1. Email/SMS provider for production password reset.
2. Push notifications for new messages.
3. Redis Pub/Sub for WebSocket scaling across multiple backend instances.
4. Group chat, if client confirms it is required.
5. Advanced fraud reporting and property flagging.
6. Admin dashboard frontend.
7. Saved/favorite properties.
8. Property view analytics.
```
