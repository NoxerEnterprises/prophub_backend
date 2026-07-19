# ProHub Backend API Documentation for Mobile Team

Version documented: upgraded async backend package with email verification, agent onboarding, documents, Paystack subscription, property management, chat, WebSocket, and admin controls.

This document is for the mobile frontend team. It explains what has been built, how each API should be used, what payloads to send, what responses to expect, and the correct integration flows.

---

## 1. Base URLs and API Prefix

Local development:

```txt
http://localhost:8000
```

Production/staging will be provided by backend deployment.

API prefix:

```txt
/api/v1
```

Swagger/OpenAPI documentation:

```txt
GET /docs
GET /openapi.json
```

Root health endpoints:

```txt
GET /
GET /health
```

Versioned endpoints use:

```txt
/api/v1/...
```

---

## 2. Authentication Model

The backend uses JWT-based authentication.

Use this header for all protected REST endpoints:

```http
Authorization: Bearer <access_token>
```

Tokens returned by the backend:

```json
{
  "access_token": "jwt-access-token",
  "refresh_token": "jwt-refresh-token",
  "token_type": "bearer",
  "expires_at": "2026-07-19T10:30:00Z"
}
```

Mobile storage rule:

```txt
Store access_token and refresh_token in secure storage.
Do not store tokens in normal AsyncStorage/plain local storage.
```

Recommended mobile token flow:

```txt
1. User logs in successfully.
2. Save access_token and refresh_token securely.
3. Use access_token in Authorization header.
4. If a protected request returns 401, call /api/v1/auth/refresh.
5. Save the new access_token and refresh_token.
6. Retry the original request.
7. If refresh fails, clear local auth state and redirect to login.
```

Important: email verification is mandatory. Unverified users can register and log in, but login returns no tokens and sends a verification-required flag. Protected endpoints reject unverified users.

---

## 3. Standard Response Format

Successful response:

```json
{
  "success": true,
  "message": "Human readable message",
  "data": {}
}
```

Paginated response:

```json
{
  "success": true,
  "message": "Records retrieved",
  "data": {
    "items": [],
    "meta": {
      "page": 1,
      "limit": 20,
      "total": 100
    }
  }
}
```

Error response:

```json
{
  "success": false,
  "message": "Error message",
  "details": null
}
```

Validation error response:

```json
{
  "success": false,
  "message": "Validation failed",
  "details": [
    {
      "type": "missing",
      "loc": ["body", "email"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

Common HTTP codes:

```txt
200 OK                 Successful read/update
201 Created            Resource created
400 Bad Request         Business-rule failure
401 Unauthorized        Missing/invalid/expired access token
403 Forbidden           Role/status/email verification/subscription restriction
404 Not Found           Resource not found
409 Conflict            Duplicate resource
422 Validation Error    Invalid request shape or field value
500 Server Error        Backend/runtime error
```

---

## 4. Core Enums

### User roles

```txt
USER
AGENT
ADMIN
SUPER_ADMIN
```

### User types

All users initially register as normal customers. Later, a customer can become an agent-type user through `/api/v1/agents/me`.

```txt
CUSTOMER
ADVERTISING_AGENT
BUSINESS_AGENT
ARTISAN
ADVERTISING
PROPERTY_DEVELOPMENT
SURVEYOR
ARCHITECT
LEGAL_DRAFTS_MAN
LANDLORD
```

Rule for now:

```txt
CUSTOMER = normal user/customer.
All other user types are treated as agent-type users with the same agent permissions.
```

### Agent statuses

```txt
PENDING
PAID
APPROVED
REJECTED
DISABLED
```

### Operating modes

```txt
STANDALONE
NOXER_MANAGED
```

Rule:

```txt
Approved CAC document    → STANDALONE
No approved CAC document → NOXER_MANAGED
```

### Subscription statuses

```txt
INACTIVE
ACTIVE
EXPIRED
CANCELLED
```

### Document types

```txt
NIN
CAC
SCUM
```

Document rules:

```txt
NIN  = mandatory for all agent-type users.
CAC  = optional, but required to operate independently.
SCUM = optional.
```

### Document statuses

```txt
PENDING
APPROVED
REJECTED
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

### Message types

```txt
TEXT
IMAGE
VIDEO
SYSTEM
```

---

## 5. Critical Mobile Flows

### 5.1 Customer registration and email verification

```txt
User registers
→ backend creates CUSTOMER account
→ backend sends verification email through Resend
→ registration response contains email_verification_required=true
→ mobile sends user to verification page
→ user enters OTP/code
→ mobile calls /auth/verify-email
→ backend marks email verified and returns access/refresh tokens
→ mobile stores tokens and enters the app
```

### 5.2 Login flow

```txt
User logs in
→ if email is verified, backend returns tokens
→ if email is not verified, backend returns email_verification_required=true and no tokens
→ mobile redirects unverified user to verification page
```

### 5.3 Become-agent flow

```txt
Verified customer opens “Become an Agent”
→ fills agent profile form
→ selects user_type
→ uploads NIN number + file
→ optionally uploads CAC number + file
→ optionally uploads SCUM number + file
→ mobile sends multipart form to POST /agents/me
→ backend creates agent profile as PENDING
→ documents are stored as PENDING
→ admin reviews documents
→ agent pays subscription
→ admin approves agent
→ approved + subscribed + NIN-approved agent can post properties
```

### 5.4 Agent posting gate

An agent can create properties only when all are true:

```txt
email is verified
role = AGENT
agent status = APPROVED
subscription_status = ACTIVE
subscription_expires_at is in the future
NIN document is APPROVED
```

### 5.5 Noxer-managed chat routing

```txt
If property owner is STANDALONE:
  customer chats with the actual property agent.

If property owner is NOXER_MANAGED:
  customer chats with configured Noxer contact/admin.
  underlying agent is not directly exposed as the chat recipient.
```

The chat response includes:

```json
{
  "routed_through_noxer": true,
  "visible_contact_type": "NOXER"
}
```

---

# 6. Health APIs

## GET `/`

Purpose: root API check.

Auth: no.

Response:

```json
{
  "success": true,
  "message": "API is running",
  "data": {
    "status": "ok",
    "docs": "/docs"
  }
}
```

## GET `/health`

Purpose: root-level health check.

Auth: no.

Response:

```json
{
  "success": true,
  "message": "API is running",
  "data": {
    "status": "ok"
  }
}
```

## GET `/api/v1/health`

Purpose: versioned health/database check.

Auth: no.

Response:

```json
{
  "success": true,
  "message": "API is running",
  "data": {
    "status": "ok",
    "database": "ok",
    "database_details": null
  }
}
```

## GET `/api/v1/status`

Purpose: service status check with version.

Auth: no.

Response:

```json
{
  "success": true,
  "message": "Service status",
  "data": {
    "api": "ok",
    "version": "0.7.0",
    "database": "ok",
    "database_details": null
  }
}
```

---

# 7. Authentication APIs

## POST `/api/v1/auth/register`

Purpose: create a normal customer account and start email verification.

Auth: no.

Request body:

```json
{
  "email": "customer@example.com",
  "full_name": "John Doe",
  "phone": "+2348012345678",
  "password": "StrongPassword123!"
}
```

Field rules:

```txt
email       required, valid email, unique
full_name   required, 2–150 chars
phone       optional, max 32 chars, unique if provided
password    required, 8–128 chars
```

Important behavior:

```txt
New users are always created as CUSTOMER.
No tokens are returned until email verification succeeds.
A verification email is sent through Resend.
In non-production, debug_verification_token and debug_otp_code may be returned for testing.
```

Success response:

```json
{
  "success": true,
  "message": "Registration successful. Please verify your email.",
  "data": {
    "user": {
      "id": "user-uuid",
      "email": "customer@example.com",
      "phone": "+2348012345678",
      "full_name": "John Doe",
      "role": "USER",
      "user_type": "CUSTOMER",
      "is_active": true,
      "is_email_verified": false,
      "email_verified_at": null,
      "created_at": "2026-07-19T10:00:00Z",
      "updated_at": "2026-07-19T10:00:00Z"
    },
    "tokens": null,
    "email_verification_required": true,
    "is_email_verified": false,
    "debug_verification_token": "dev-only-token",
    "debug_otp_code": "123456"
  }
}
```

Mobile behavior:

```txt
1. Do not treat registration as logged-in access.
2. Redirect user to email verification screen.
3. Ask for OTP/code from email.
4. Call /auth/verify-email.
```

---

## POST `/api/v1/auth/verify-email`

Purpose: verify a new user’s email and issue tokens.

Auth: no.

Request body:

```json
{
  "email": "customer@example.com",
  "verification_token": "optional-verification-token",
  "otp_code": "123456"
}
```

Notes:

```txt
otp_code is required.
verification_token is optional but supported.
If mobile only has OTP, send email + otp_code.
```

Success response:

```json
{
  "success": true,
  "message": "Email verified successfully",
  "data": {
    "verified": true,
    "user": {
      "id": "user-uuid",
      "email": "customer@example.com",
      "role": "USER",
      "user_type": "CUSTOMER",
      "is_email_verified": true,
      "email_verified_at": "2026-07-19T10:05:00Z"
    },
    "tokens": {
      "access_token": "jwt-access-token",
      "refresh_token": "jwt-refresh-token",
      "token_type": "bearer",
      "expires_at": "2026-07-19T10:35:00Z"
    }
  }
}
```

Mobile behavior:

```txt
1. Submit OTP/code.
2. Save returned access_token and refresh_token.
3. Enter the app.
```

Common errors:

```txt
400 invalid/expired verification token
400 invalid code
400 max attempts exceeded
422 invalid payload
```

---

## POST `/api/v1/auth/resend-verification`

Purpose: resend verification email/code.

Auth: no.

Request body:

```json
{
  "email": "customer@example.com"
}
```

Response:

```json
{
  "success": true,
  "message": "Verification email processed",
  "data": {
    "email_verification_required": true,
    "email": "customer@example.com",
    "debug_verification_token": "dev-only-token",
    "debug_otp_code": "123456"
  }
}
```

Mobile behavior:

```txt
Use this from the verification screen when the user taps “Resend code”.
```

---

## POST `/api/v1/auth/login`

Purpose: authenticate verified users.

Auth: no.

Request body:

```json
{
  "email": "customer@example.com",
  "password": "StrongPassword123!"
}
```

Response when verified:

```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "user": {
      "id": "user-uuid",
      "email": "customer@example.com",
      "full_name": "John Doe",
      "role": "USER",
      "user_type": "CUSTOMER",
      "is_active": true,
      "is_email_verified": true
    },
    "tokens": {
      "access_token": "jwt-access-token",
      "refresh_token": "jwt-refresh-token",
      "token_type": "bearer",
      "expires_at": "2026-07-19T10:35:00Z"
    },
    "email_verification_required": false,
    "is_email_verified": true
  }
}
```

Response when not verified:

```json
{
  "success": true,
  "message": "Email verification required",
  "data": {
    "user": {
      "id": "user-uuid",
      "email": "customer@example.com",
      "role": "USER",
      "user_type": "CUSTOMER",
      "is_email_verified": false
    },
    "tokens": null,
    "email_verification_required": true,
    "is_email_verified": false,
    "debug_verification_token": "dev-only-token-if-generated",
    "debug_otp_code": "dev-only-code-if-generated"
  }
}
```

Mobile behavior:

```txt
If data.email_verification_required is true:
  redirect to verification screen.
  do not enter main app.

If tokens exist:
  save tokens securely and enter the app.
```

---

## POST `/api/v1/auth/refresh`

Purpose: rotate refresh token and issue new access token.

Auth: no.

Request body:

```json
{
  "refresh_token": "existing-refresh-token"
}
```

Response:

```json
{
  "success": true,
  "message": "Token refreshed",
  "data": {
    "access_token": "new-access-token",
    "refresh_token": "new-refresh-token",
    "token_type": "bearer",
    "expires_at": "2026-07-19T11:00:00Z"
  }
}
```

Important: refresh token rotation is enabled. Replace both local tokens after refresh.

---

## POST `/api/v1/auth/logout`

Purpose: revoke refresh token.

Auth: no.

Request body:

```json
{
  "refresh_token": "current-refresh-token"
}
```

Response:

```json
{
  "success": true,
  "message": "Logout successful",
  "data": {
    "logged_out": true
  }
}
```

Mobile behavior:

```txt
Always clear local tokens after logout, even if network fails.
```

---

## GET `/api/v1/auth/me`

Purpose: get current authenticated user profile and status flags.

Auth: yes.

Response:

```json
{
  "success": true,
  "message": "Current user",
  "data": {
    "id": "user-uuid",
    "email": "user@example.com",
    "phone": "+2348012345678",
    "full_name": "John Doe",
    "role": "AGENT",
    "user_type": "BUSINESS_AGENT",
    "is_active": true,
    "is_email_verified": true,
    "email_verified_at": "2026-07-19T10:05:00Z",
    "created_at": "2026-07-19T10:00:00Z",
    "updated_at": "2026-07-19T10:05:00Z",
    "agent_status": "APPROVED",
    "agent_operating_mode": "STANDALONE",
    "subscription_status": "ACTIVE",
    "subscription_expires_at": "2027-07-19T10:10:00Z",
    "email_verification_required": false,
    "is_super_admin": false
  }
}
```

Use this on app startup to restore user state.

---

## POST `/api/v1/auth/request-reset`

Purpose: request password reset token/OTP.

Auth: no.

Request body:

```json
{
  "email": "user@example.com"
}
```

Response:

```json
{
  "success": true,
  "message": "Password reset requested",
  "data": {
    "message": "If this email exists, password reset instructions have been generated.",
    "debug_reset_token": "dev-only-reset-token",
    "debug_otp_code": "123456"
  }
}
```

Note: password reset email delivery may need to be wired into the same email provider flow if the current build only returns debug values in non-production.

---

## POST `/api/v1/auth/verify-reset`

Purpose: verify password reset token/OTP.

Auth: no.

Request body:

```json
{
  "reset_token": "reset-token",
  "otp_code": "123456"
}
```

Response:

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

## POST `/api/v1/auth/reset-password`

Purpose: reset password using reset token and OTP.

Auth: no.

Request body:

```json
{
  "reset_token": "reset-token",
  "otp_code": "123456",
  "new_password": "NewStrongPassword123!"
}
```

Response:

```json
{
  "success": true,
  "message": "Password reset successful",
  "data": {
    "reset": true
  }
}
```

---

# 8. Agent APIs

## POST `/api/v1/agents/me`

Purpose: submit “Become an Agent” onboarding form.

Auth: yes. User must be verified.

Content type:

```txt
multipart/form-data
```

Required fields:

```txt
user_type       non-CUSTOMER UserType
business_name   string, 2–160 chars
nin_number      string, 2–120 chars
nin_file        uploaded file
```

Optional fields:

```txt
business_phone
business_email
license_number
address
city
state
country            default Nigeria
cac_number
cac_file
scum_number
scum_file
```

Important validation:

```txt
user_type cannot be CUSTOMER.
NIN number and NIN file are mandatory.
CAC number and CAC file must be submitted together.
SCUM number and SCUM file must be submitted together.
```

Example multipart fields:

```txt
user_type=BUSINESS_AGENT
business_name=Prime Homes Realty
business_phone=+2348012345678
business_email=agency@example.com
nin_number=12345678901
nin_file=<file>
cac_number=RC123456
cac_file=<file>
scum_number=SCUM-12345
scum_file=<file>
```

Success response:

```json
{
  "success": true,
  "message": "Agent profile submitted for review",
  "data": {
    "id": "agent-profile-uuid",
    "user_id": "user-uuid",
    "user_type": "BUSINESS_AGENT",
    "operating_mode": "NOXER_MANAGED",
    "business_name": "Prime Homes Realty",
    "business_phone": "+2348012345678",
    "business_email": "agency@example.com",
    "license_number": null,
    "address": null,
    "city": null,
    "state": null,
    "country": "Nigeria",
    "status": "PENDING",
    "previous_status": null,
    "status_note": null,
    "subscription_status": "INACTIVE",
    "subscription_started_at": null,
    "subscription_expires_at": null,
    "last_subscription_transaction_id": null,
    "approved_at": null,
    "rejected_at": null,
    "disabled_at": null,
    "created_at": "2026-07-19T10:00:00Z",
    "updated_at": "2026-07-19T10:00:00Z",
    "documents": [
      {
        "id": "document-uuid",
        "document_type": "NIN",
        "document_number": "12345678901",
        "file_url": "https://...",
        "storage_path": "documents/...",
        "status": "PENDING"
      }
    ]
  }
}
```

Mobile behavior:

```txt
After success, show “Submitted for review” and payment/subscription prompt depending on product flow.
Do not show property posting features until /auth/me shows APPROVED + ACTIVE subscription.
```

---

## GET `/api/v1/agents/me`

Purpose: get current user’s agent profile.

Auth: yes.

Response includes agent profile and uploaded documents.

Use for:

```txt
Agent dashboard
Agent onboarding progress
Checking status: PENDING/PAID/APPROVED/REJECTED/DISABLED
Checking operating mode: STANDALONE/NOXER_MANAGED
Checking subscription status
```

---

## PATCH `/api/v1/agents/me`

Purpose: update basic agent profile fields.

Auth: yes.

Request body:

```json
{
  "business_name": "Prime Homes and Lands",
  "business_phone": "+2348099999999",
  "business_email": "new-email@example.com",
  "license_number": "LIC-123",
  "address": "12 Example Street",
  "city": "Ikeja",
  "state": "Lagos",
  "country": "Nigeria"
}
```

Send only fields that changed.

Response: updated agent profile.

---

## GET `/api/v1/agents/me/properties`

Purpose: list properties belonging to current approved agent.

Auth: yes, approved active agent only.

Query params:

```txt
page   default 1, min 1
limit  default 20, 1–100
```

Response:

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

# 9. Document APIs

Documents are stored in Supabase Storage and tracked in the database. Every document has a document number and uploaded file.

## GET `/api/v1/documents/me`

Purpose: list current user’s uploaded documents.

Auth: yes.

Response:

```json
{
  "success": true,
  "message": "Documents retrieved",
  "data": [
    {
      "id": "document-uuid",
      "user_id": "user-uuid",
      "agent_profile_id": "agent-profile-uuid",
      "document_type": "NIN",
      "document_number": "12345678901",
      "file_url": "https://...",
      "storage_path": "documents/...",
      "content_type": "application/pdf",
      "file_size_bytes": 100000,
      "status": "PENDING",
      "rejection_reason": null,
      "reviewed_by_id": null,
      "reviewed_at": null,
      "created_at": "2026-07-19T10:00:00Z",
      "updated_at": "2026-07-19T10:00:00Z"
    }
  ]
}
```

## POST `/api/v1/documents/me`

Purpose: upload or replace a document after agent profile creation.

Auth: yes. User must already have an agent profile.

Content type:

```txt
multipart/form-data
```

Fields:

```txt
document_type=NIN | CAC | SCUM
document_number=alphanumeric-value
file=<uploaded file>
```

Response: uploaded document.

Use cases:

```txt
Agent uploads CAC later to become STANDALONE.
Agent replaces rejected NIN document.
Agent uploads optional SCUM document.
```

---

# 10. Payment APIs

Paystack is used for agent subscription payments.

Subscription duration is controlled by backend environment variable:

```env
SUBSCRIPTION_DURATION_MONTHS=1..12
```

Examples:

```txt
1  = monthly
6  = six months
12 = yearly
```

Payment amount is controlled by backend environment variable:

```env
AGENT_SUBSCRIPTION_FEE=10000
PAYSTACK_CURRENCY=NGN
```

Mobile must never send or control the amount.

## POST `/api/v1/payments/initialize`

Purpose: initialize Paystack subscription payment for current agent.

Auth: yes. User must be an agent.

Request body:

```json
{
  "callback_url": "https://your-mobile-or-web-callback-url.com/payment-result"
}
```

`callback_url` is optional. If omitted, backend uses configured `PAYSTACK_CALLBACK_URL`.

Success response:

```json
{
  "success": true,
  "message": "Subscription payment initialized",
  "data": {
    "reference": "PH_SUB_abc123",
    "amount": "10000.00",
    "currency": "NGN",
    "subscription_duration_months": 12,
    "authorization_url": "https://checkout.paystack.com/...",
    "access_code": "paystack-access-code",
    "public_key": "pk_test_xxx"
  }
}
```

Mobile behavior:

```txt
1. Call initialize.
2. Open authorization_url in Paystack checkout/webview/browser.
3. After Paystack callback returns, call /payments/verify/{reference}.
4. Update agent onboarding UI based on returned subscription_status.
```

---

## GET `/api/v1/payments/verify/{reference}`

Purpose: verify a Paystack transaction after checkout.

Auth: yes. Transaction must belong to current user/agent.

Response:

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
      "payment_type": "AGENT_SUBSCRIPTION",
      "reference": "PH_SUB_abc123",
      "amount": "10000.00",
      "currency": "NGN",
      "status": "SUCCESS",
      "authorization_url": "https://checkout.paystack.com/...",
      "access_code": "paystack-access-code",
      "subscription_duration_months": 12,
      "subscription_period_start": "2026-07-19T10:00:00Z",
      "subscription_period_end": "2027-07-19T10:00:00Z",
      "paid_at": "2026-07-19T10:00:00Z",
      "verified_at": "2026-07-19T10:00:00Z",
      "failure_reason": null,
      "created_at": "2026-07-19T09:55:00Z",
      "updated_at": "2026-07-19T10:00:00Z"
    },
    "agent_status": "PAID",
    "subscription_status": "ACTIVE",
    "subscription_expires_at": "2027-07-19T10:00:00Z"
  }
}
```

Important behavior:

```txt
Successful payment activates subscription.
If agent is not already APPROVED/DISABLED, status becomes PAID.
Admin approval is still required before property posting.
```

---

## POST `/api/v1/payments/webhook`

Purpose: Paystack webhook endpoint.

Auth: no JWT. Uses Paystack signature header.

Header:

```http
x-paystack-signature: <signature>
```

Body: raw Paystack webhook event.

Response:

```json
{
  "success": true,
  "message": "Webhook processed",
  "data": {
    "processed": true
  }
}
```

Mobile team does not call this endpoint. It is configured in Paystack dashboard.

---

## GET `/api/v1/payments/me`

Purpose: list current user’s payment transactions.

Auth: yes.

Query params:

```txt
page   default 1
limit  default 20, max 100
```

Response: paginated `TransactionResponse` list.

---

# 11. Property APIs

## POST `/api/v1/properties`

Purpose: create property listing.

Auth: yes, approved active agent only.

Gate required by backend:

```txt
email verified
role AGENT
agent status APPROVED
subscription ACTIVE and not expired
NIN document APPROVED
```

Request body:

```json
{
  "title": "Land for Sale in Lekki",
  "description": "Dry land in a developed estate with good road access.",
  "price": "15000000.00",
  "currency": "NGN",
  "country": "Nigeria",
  "state": "Lagos",
  "local_government": "Eti-Osa",
  "community": "Lekki",
  "address_details": "Phase 2 area",
  "category": "LAND",
  "listing_type": "SALE",
  "status": "AVAILABLE",
  "is_published": true
}
```

Response: created `PropertyResponse`.

---

## GET `/api/v1/properties`

Purpose: list public properties.

Auth: no.

Query params:

```txt
page   default 1
limit  default 20, max 100
```

Response: paginated property list.

---

## GET `/api/v1/properties/search`

Purpose: public property search/filter.

Auth: no.

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
page
limit
```

Allowed sort values:

```txt
newest
oldest
price_asc
price_desc
```

Example:

```txt
GET /api/v1/properties/search?state=Lagos&category=LAND&min_price=5000000&sort=price_asc&page=1&limit=20
```

Response: paginated property list.

---

## GET `/api/v1/properties/{property_id}`

Purpose: get public property detail.

Auth: no.

Response: `PropertyResponse`.

---

## PATCH `/api/v1/properties/{property_id}`

Purpose: update own property.

Auth: yes, approved active agent only. Agent must own property.

Request body: send only changed fields.

```json
{
  "price": "14000000.00",
  "status": "AVAILABLE",
  "is_published": true
}
```

Response: updated `PropertyResponse`.

---

## DELETE `/api/v1/properties/{property_id}`

Purpose: soft-delete own property.

Auth: yes, approved active agent only. Agent must own property.

Response:

```json
{
  "success": true,
  "message": "Property deleted",
  "data": {
    "deleted": true
  }
}
```

---

## POST `/api/v1/properties/{property_id}/media`

Purpose: upload property image.

Auth: yes, approved active agent only. Agent must own property.

Content type:

```txt
multipart/form-data
```

Fields:

```txt
file=<image file>
position=0
```

Supported property media:

```txt
image/jpeg
image/png
image/webp
```

Response:

```json
{
  "success": true,
  "message": "Property image uploaded",
  "data": {
    "id": "media-uuid",
    "property_id": "property-uuid",
    "file_url": "https://...",
    "storage_path": "properties/property-uuid/media-uuid.jpg",
    "media_type": "IMAGE",
    "content_type": "image/jpeg",
    "file_size_bytes": 100000,
    "position": 0,
    "created_at": "2026-07-19T10:00:00Z",
    "updated_at": "2026-07-19T10:00:00Z"
  }
}
```

---

## DELETE `/api/v1/properties/{property_id}/media/{media_id}`

Purpose: delete property image.

Auth: yes, approved active agent only. Agent must own property.

Response:

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

# 12. Chat APIs

The backend supports persistent private chat, text messages, image/video media messages, unread counts, REST fallback, and WebSocket real-time messaging.

## POST `/api/v1/chats`

Purpose: start or retrieve private chat.

Auth: yes, verified user.

Request body:

```json
{
  "agent_id": "agent-profile-uuid",
  "property_id": "property-uuid",
  "initial_message": "Hello, I am interested in this property."
}
```

Rules:

```txt
Either agent_id or property_id is required.
If property_id is provided, backend resolves the property owner.
If property owner is STANDALONE, chat target is actual agent.
If property owner is NOXER_MANAGED, chat target is configured Noxer contact/admin.
Only approved agents can be contacted.
```

Response:

```json
{
  "success": true,
  "message": "Chat ready",
  "data": {
    "id": "chat-uuid",
    "chat_type": "PRIVATE",
    "property_id": "property-uuid",
    "created_by_id": "customer-user-uuid",
    "target_user_id": "noxer-or-agent-user-uuid",
    "underlying_agent_id": "actual-agent-profile-uuid",
    "routed_through_noxer": true,
    "visible_contact_type": "NOXER",
    "title": "Land for Sale in Lekki",
    "last_message_id": "message-uuid",
    "last_message_at": "2026-07-19T10:00:00Z",
    "created_at": "2026-07-19T10:00:00Z",
    "updated_at": "2026-07-19T10:00:00Z",
    "participants": [],
    "property": {
      "id": "property-uuid",
      "title": "Land for Sale in Lekki",
      "state": "Lagos",
      "community": "Lekki"
    }
  }
}
```

Mobile display rule:

```txt
If visible_contact_type = NOXER, display Noxer as the contact.
If visible_contact_type = AGENT, display actual agent information.
```

---

## GET `/api/v1/chats`

Purpose: list current user’s chats.

Auth: yes.

Query params:

```txt
page   default 1
limit  default 20, max 100
```

Response: paginated `ChatListItem` list with `last_message` and `unread_count`.

---

## GET `/api/v1/chats/{chat_id}`

Purpose: get a chat detail.

Auth: yes. User must be a participant.

Response: `ChatResponse`.

---

## GET `/api/v1/chats/{chat_id}/messages`

Purpose: list messages in a chat.

Auth: yes. User must be a participant.

Query params:

```txt
page   default 1
limit  default 50, max 100
```

Response: paginated `MessageResponse` list.

---

## POST `/api/v1/chats/{chat_id}/messages`

Purpose: send text message through REST.

Auth: yes. User must be a participant.

Request body:

```json
{
  "content": "Is this property still available?",
  "message_type": "TEXT",
  "client_message_id": "mobile-local-uuid-optional"
}
```

Response:

```json
{
  "success": true,
  "message": "Message sent",
  "data": {
    "id": "message-uuid",
    "chat_id": "chat-uuid",
    "sender_id": "user-uuid",
    "content": "Is this property still available?",
    "message_type": "TEXT",
    "media_url": null,
    "media_path": null,
    "media_content_type": null,
    "media_size_bytes": null,
    "client_message_id": "mobile-local-uuid-optional",
    "read_at": null,
    "deleted_at": null,
    "created_at": "2026-07-19T10:00:00Z",
    "updated_at": "2026-07-19T10:00:00Z"
  }
}
```

Note: this endpoint also broadcasts the saved message to connected WebSocket participants.

---

## POST `/api/v1/chats/{chat_id}/messages/media`

Purpose: upload image or video chat message.

Auth: yes. User must be a participant.

Content type:

```txt
multipart/form-data
```

Fields:

```txt
file=<image-or-video-file>
content=optional caption
client_message_id=optional mobile local UUID
```

Supported media:

```txt
Images: image/jpeg, image/png, image/webp
Videos: video/mp4, video/webm, video/quicktime
```

Response: `MessageResponse` with:

```json
{
  "message_type": "IMAGE",
  "media_url": "https://...",
  "media_path": "chats/chat-uuid/message-uuid.jpg",
  "media_content_type": "image/jpeg",
  "media_size_bytes": 120000
}
```

or:

```json
{
  "message_type": "VIDEO",
  "media_url": "https://...",
  "media_path": "chats/chat-uuid/message-uuid.mp4",
  "media_content_type": "video/mp4",
  "media_size_bytes": 5000000
}
```

Important: do not upload image/video through WebSocket. Use this REST endpoint. The backend broadcasts the created media message after upload.

---

## PATCH `/api/v1/chats/{chat_id}/read`

Purpose: mark chat as read for current user.

Auth: yes. User must be a participant.

Response:

```json
{
  "success": true,
  "message": "Chat marked as read",
  "data": {
    "chat_id": "chat-uuid",
    "unread_count": 0,
    "last_read_at": "2026-07-19T10:00:00Z"
  }
}
```

---

# 13. WebSocket Chat API

Endpoint:

```txt
WS /api/v1/ws/chats/{chat_id}?token=<access_token>
```

Production URL example:

```txt
wss://your-backend-domain.com/api/v1/ws/chats/{chat_id}?token=<access_token>
```

Rules:

```txt
Token must be a valid access token.
User must be email verified.
User must be a chat participant.
Connection is rejected if the token is invalid or user is unauthorized.
```

## Connection-ready event

After successful connection, backend sends:

```json
{
  "type": "connection.ready",
  "data": {
    "chat_id": "chat-uuid",
    "user_id": "user-uuid"
  }
}
```

## Ping/pong

Client sends:

```json
{
  "type": "ping",
  "data": {}
}
```

Server replies:

```json
{
  "type": "pong",
  "data": {}
}
```

## Send text message via WebSocket

Client sends:

```json
{
  "type": "message.send",
  "data": {
    "content": "Hello, is this property still available?",
    "client_message_id": "mobile-local-uuid"
  }
}
```

Server broadcasts:

```json
{
  "type": "message.created",
  "data": {
    "id": "message-uuid",
    "chat_id": "chat-uuid",
    "sender_id": "user-uuid",
    "content": "Hello, is this property still available?",
    "message_type": "TEXT",
    "client_message_id": "mobile-local-uuid",
    "created_at": "2026-07-19T10:00:00Z",
    "updated_at": "2026-07-19T10:00:00Z"
  }
}
```

## Mark read via WebSocket

Client sends:

```json
{
  "type": "chat.read",
  "data": {}
}
```

Server broadcasts:

```json
{
  "type": "chat.read",
  "data": {
    "chat_id": "chat-uuid",
    "user_id": "user-uuid",
    "last_read_at": "2026-07-19T10:00:00Z"
  }
}
```

## Unsupported event

Server sends:

```json
{
  "type": "error",
  "data": {
    "message": "Unsupported event type"
  }
}
```

Mobile WebSocket recommendation:

```txt
Use REST for image/video upload.
Use WebSocket for live text messages and receiving broadcasts.
Reconnect automatically when network changes.
On reconnect, call GET /chats/{chat_id}/messages to sync missed messages.
```

---

# 14. Admin APIs

Admin endpoints require `ADMIN` or `SUPER_ADMIN`, except admin-management endpoints which require `SUPER_ADMIN`.

## 14.1 Super-admin admin management

### POST `/api/v1/admin/admins`

Purpose: create another admin account.

Auth: super admin only.

Request body:

```json
{
  "email": "admin2@example.com",
  "full_name": "Admin Two",
  "phone": "+2348012345678",
  "password": "StrongPassword123!",
  "is_super_admin": false,
  "title": "Operations Admin",
  "permissions": {
    "manage_agents": true,
    "manage_properties": true,
    "view_transactions": true,
    "view_activity_logs": true
  }
}
```

Response: `AdminProfileResponse`.

### GET `/api/v1/admin/admins`

Purpose: list admins.

Auth: super admin only.

Query params:

```txt
page
limit
```

### GET `/api/v1/admin/admins/{admin_id}`

Purpose: view admin profile.

Auth: super admin only.

### PATCH `/api/v1/admin/admins/{admin_id}`

Purpose: update admin user details/permissions.

Auth: super admin only.

Request body:

```json
{
  "full_name": "Updated Admin Name",
  "phone": "+2348099999999",
  "title": "Senior Admin",
  "permissions": {
    "manage_agents": true,
    "manage_properties": false
  }
}
```

### PATCH `/api/v1/admin/admins/{admin_id}/disable`

Purpose: disable admin account.

Auth: super admin only.

### PATCH `/api/v1/admin/admins/{admin_id}/enable`

Purpose: re-enable admin account.

Auth: super admin only.

---

## 14.2 Admin agent management

### GET `/api/v1/admin/agents`

Purpose: list/filter agent profiles.

Auth: admin/super admin.

Query params:

```txt
page
limit
status
user_type
operating_mode
subscription_status
q
```

Example:

```txt
GET /api/v1/admin/agents?status=PENDING&user_type=BUSINESS_AGENT&operating_mode=NOXER_MANAGED&page=1&limit=20
```

### GET `/api/v1/admin/agents/{agent_id}`

Purpose: get single agent with user and documents.

Auth: admin/super admin.

### PATCH `/api/v1/admin/agents/{agent_id}/approve`

Purpose: approve an agent.

Auth: admin/super admin.

Request body:

```json
{
  "note": "NIN approved and subscription active.",
  "allow_override": false,
  "allow_unpaid_override": false
}
```

Normal approval requirements:

```txt
NIN document must be APPROVED.
Subscription must be ACTIVE and not expired.
Agent must not be DISABLED.
```

`allow_override` exists for emergency/admin testing. Do not expose it carelessly in production UI.

### PATCH `/api/v1/admin/agents/{agent_id}/reject`

Request body:

```json
{
  "note": "NIN document does not match submitted details."
}
```

### PATCH `/api/v1/admin/agents/{agent_id}/disable`

Request body:

```json
{
  "note": "Disabled for suspicious activity."
}
```

### PATCH `/api/v1/admin/agents/{agent_id}/enable`

Request body:

```json
{
  "note": "Review completed. Account restored."
}
```

---

## 14.3 Admin document review

Preferred admin document endpoints:

```txt
GET   /api/v1/admin/documents
PATCH /api/v1/admin/documents/{document_id}/approve
PATCH /api/v1/admin/documents/{document_id}/reject
```

There are also document-prefixed equivalents:

```txt
GET   /api/v1/documents/admin
PATCH /api/v1/documents/admin/{document_id}/approve
PATCH /api/v1/documents/admin/{document_id}/reject
```

Use the `/api/v1/admin/documents...` version in new mobile/admin UI.

### GET `/api/v1/admin/documents`

Purpose: list/filter uploaded documents.

Auth: admin/super admin.

Query params:

```txt
status
 document_type
user_id
agent_profile_id
page
limit
```

Example:

```txt
GET /api/v1/admin/documents?status=PENDING&document_type=NIN&page=1&limit=20
```

### PATCH `/api/v1/admin/documents/{document_id}/approve`

Purpose: approve a document.

Request body:

```json
{
  "note": "Document verified."
}
```

Important behavior:

```txt
Approving CAC switches the agent operating_mode to STANDALONE.
Approving NIN satisfies mandatory identity requirement.
```

### PATCH `/api/v1/admin/documents/{document_id}/reject`

Purpose: reject a document.

Request body:

```json
{
  "reason": "Uploaded document is unreadable. Please upload a clearer copy."
}
```

Important behavior:

```txt
Rejecting CAC keeps/reverts the agent to NOXER_MANAGED.
```

---

## 14.4 Admin property oversight

### GET `/api/v1/admin/properties`

Purpose: list all properties, including hidden/deleted when requested.

Auth: admin/super admin.

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
include_deleted
page
limit
```

### GET `/api/v1/admin/properties/{property_id}`

Purpose: get property detail regardless of public visibility.

Auth: admin/super admin.

### PATCH `/api/v1/admin/properties/{property_id}/hide`

Purpose: hide a property from public search/listings.

Request body:

```json
{
  "note": "Suspicious listing. Hidden pending review."
}
```

### PATCH `/api/v1/admin/properties/{property_id}/restore`

Purpose: restore hidden property.

Request body:

```json
{
  "note": "Review completed.",
  "status": "AVAILABLE",
  "is_published": true
}
```

### DELETE `/api/v1/admin/properties/{property_id}`

Purpose: admin soft-delete property.

Auth: admin/super admin.

Query param:

```txt
note=Fraudulent listing confirmed
```

Response:

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

## 14.5 Admin transactions

### GET `/api/v1/admin/transactions`

Purpose: list Paystack/subscription transactions.

Auth: admin/super admin.

Query params:

```txt
status
page
limit
```

Example:

```txt
GET /api/v1/admin/transactions?status=SUCCESS&page=1&limit=20
```

Response: paginated `TransactionResponse` list.

---

## 14.6 Admin activity logs

### GET `/api/v1/admin/activity-logs`

Purpose: audit trail of admin/system actions.

Auth: admin/super admin.

Query params:

```txt
page
limit
```

Response:

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
        "description": "Approved agent Prime Homes Realty",
        "metadata_json": {},
        "created_at": "2026-07-19T10:00:00Z"
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

# 15. Mobile Integration Sequences

## 15.1 First-time customer

```txt
POST /auth/register
→ show verify email screen
POST /auth/verify-email
→ save tokens
GET /auth/me
→ open customer home
```

## 15.2 Existing unverified user login

```txt
POST /auth/login
→ data.email_verification_required = true
→ redirect to verify email screen
POST /auth/resend-verification if needed
POST /auth/verify-email
→ save tokens
```

## 15.3 Become an agent

```txt
GET /auth/me
→ confirm user is verified
POST /agents/me as multipart/form-data
→ show submitted status
GET /agents/me to show review/subscription status
POST /payments/initialize
→ open Paystack authorization_url
GET /payments/verify/{reference}
→ subscription becomes ACTIVE
Admin approves NIN and agent profile
GET /auth/me
→ if APPROVED + ACTIVE, show property tools
```

## 15.4 Property posting

```txt
POST /properties
POST /properties/{property_id}/media
GET /agents/me/properties
PATCH /properties/{property_id}
DELETE /properties/{property_id}
```

## 15.5 Customer property search and chat

```txt
GET /properties/search
GET /properties/{property_id}
POST /chats with property_id and optional initial_message
Connect WS /ws/chats/{chat_id}?token=<access_token>
GET /chats/{chat_id}/messages for history
POST /chats/{chat_id}/messages for REST fallback
POST /chats/{chat_id}/messages/media for images/videos
PATCH /chats/{chat_id}/read
```

## 15.6 Admin review workflow

```txt
Admin login
GET /admin/agents?status=PENDING
GET /admin/documents?status=PENDING
PATCH /admin/documents/{nin_id}/approve
PATCH /admin/documents/{cac_id}/approve if independent operation is valid
GET /admin/transactions?status=SUCCESS
PATCH /admin/agents/{agent_id}/approve
```

---

# 16. Manual Backend Configuration Needed

These are not mobile tasks, but the mobile team should understand external dependencies.

## Environment variables

```env
DATABASE_URL="your-supabase-postgres-url"
SUPABASE_URL="https://your-project-ref.supabase.co"
SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
SUPABASE_STORAGE_BUCKET="property-media"

JWT_SECRET_KEY="your-generated-secret"

RESEND_API_KEY="re_xxxxx"
EMAIL_FROM="ProHub <noreply@yourdomain.com>"
FRONTEND_EMAIL_VERIFY_URL="https://your-mobile-or-web-url.com/verify-email"

PAYSTACK_PUBLIC_KEY="pk_test_or_live_xxxxx"
PAYSTACK_SECRET_KEY="sk_test_or_live_xxxxx"
PAYSTACK_WEBHOOK_SECRET=""
PAYSTACK_CURRENCY="NGN"
PAYSTACK_CALLBACK_URL="https://your-mobile-or-web-url.com/payment/callback"
AGENT_SUBSCRIPTION_FEE=10000
SUBSCRIPTION_DURATION_MONTHS=12

NOXER_CONTACT_USER_ID="super-admin-or-noxer-admin-user-id"

MAX_PROPERTY_IMAGE_SIZE_MB=5
MAX_CHAT_IMAGE_SIZE_MB=5
MAX_CHAT_VIDEO_SIZE_MB=50
MAX_DOCUMENT_SIZE_MB=10
```

`SUBSCRIPTION_DURATION_MONTHS` accepts any integer from 1 to 12.

## Supabase Storage bucket

Bucket name:

```txt
property-media
```

Recommended bucket access for MVP:

```txt
Public bucket: Yes
```

Recommended allowed content types:

```txt
image/jpeg
image/png
image/webp
application/pdf
video/mp4
video/webm
video/quicktime
```

## Paystack webhook URL

Configure in Paystack dashboard:

```txt
https://your-backend-domain.com/api/v1/payments/webhook
```

## Noxer contact identity

For NOXER_MANAGED listing chats, backend uses:

```env
NOXER_CONTACT_USER_ID="admin-user-uuid"
```

If empty, backend attempts to use the first active super admin.

---

# 17. Current Scope Covered

Built and available:

```txt
Async FastAPI backend
Supabase PostgreSQL integration
Supabase Storage upload support
JWT auth
Refresh token rotation
Mandatory email verification
Password reset foundation
Customer registration
Become-agent onboarding
UserType support
NIN/CAC/SCUM document upload
Admin document review
OperatingMode STANDALONE/NOXER_MANAGED
Configurable 1–12 month subscription duration
Paystack subscription initialization/verification/webhook
Agent approval/rejection/disable/enable
Super-admin admin-management APIs
Property CRUD
Property media upload/delete
Property search/filter/pagination
Admin property moderation
Persistent private chat
Text/image/video chat messages
WebSocket real-time chat
Noxer-managed chat routing
Admin transactions
Admin activity logs
```

Not included / future scope:

```txt
Native mobile app UI
Web frontend/admin dashboard UI
Push notifications
Escrow/wallet/customer-service payment processing
Commission/remittance logic
Bank account management
Group chat production workflow
Redis-based multi-instance WebSocket scaling
Automated KYC verification
```

---

# 18. Frontend Implementation Warnings

1. Do not allow users into the main platform if `email_verification_required=true`.
2. Do not show property creation tools unless `/auth/me` confirms `agent_status=APPROVED` and `subscription_status=ACTIVE`.
3. Do not let mobile decide payment amount or subscription duration; backend controls it.
4. Do not expose underlying agent contact details when `visible_contact_type=NOXER` or `routed_through_noxer=true`.
5. Use REST upload for image/video chat messages, then listen for WebSocket broadcasts.
6. On WebSocket reconnect, always refetch messages through REST to catch missed events.
7. For admin document review, approving CAC affects operating mode; approving NIN affects eligibility for agent approval/property posting.
8. Store all tokens securely.

