# Paystack + Chat Integration Guide

This package builds on the existing async FastAPI backend and adds:

- Paystack agent-verification payment flow
- Transaction persistence
- Paystack transaction verification
- Paystack webhook processing with signature verification
- Agent status update from `PENDING` / `REJECTED` to `PAID` after successful payment
- Persistent private chat
- REST message sending
- WebSocket real-time chat
- Text, image, and video chat messages
- Admin transaction listing

## 1. Environment variables you must configure

Update `.env`:

```env
PAYSTACK_PUBLIC_KEY="pk_test_or_live_xxxxx"
PAYSTACK_SECRET_KEY="sk_test_or_live_xxxxx"
PAYSTACK_WEBHOOK_SECRET=""
PAYSTACK_CURRENCY="NGN"
AGENT_VERIFICATION_FEE=10000
PAYSTACK_CALLBACK_URL="https://your-mobile-or-web-callback-url.com/payment-result"
PAYSTACK_BASE_URL="https://api.paystack.co"

SUPABASE_URL="https://your-project-ref.supabase.co"
SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
SUPABASE_STORAGE_BUCKET="property-media"

MAX_CHAT_IMAGE_SIZE_MB=5
MAX_CHAT_VIDEO_SIZE_MB=50
```

`AGENT_VERIFICATION_FEE` is in major currency unit. Example: `10000` means ₦10,000. The backend converts this to kobo before sending to Paystack.

`PAYSTACK_WEBHOOK_SECRET` can be left empty. If empty, the backend uses `PAYSTACK_SECRET_KEY` for webhook signature verification.

## 2. Supabase Storage task

Use the same public bucket used for property media:

```txt
Bucket name: property-media
Public: Yes
Allowed image types: image/jpeg, image/png, image/webp
Allowed video types: video/mp4, video/webm, video/quicktime
Recommended max file size: 50 MB
```

Chat files are stored under:

```txt
chats/{chat_id}/{uuid}.{ext}
```

Property files remain under:

```txt
properties/{property_id}/{uuid}.{ext}
```

## 3. Run migrations

```bash
alembic upgrade head
```

This creates:

```txt
transactions
chats
chat_participants
messages
```

## 4. Paystack dashboard task

In Paystack dashboard, configure webhook URL:

```txt
https://your-backend-domain.com/api/v1/payments/webhook
```

For local testing, expose your local backend with a tunnel and use:

```txt
https://your-tunnel-url/api/v1/payments/webhook
```

## 5. Payment flow

1. Agent creates profile.
2. Agent calls `POST /api/v1/payments/initialize`.
3. Backend creates a pending transaction and calls Paystack.
4. Mobile app opens returned `authorization_url`.
5. After checkout, mobile calls `GET /api/v1/payments/verify/{reference}`.
6. Paystack webhook can also confirm the transaction.
7. Backend updates transaction to `SUCCESS`.
8. Backend updates agent status to `PAID`.
9. Admin approves the agent.
10. Agent can create properties after becoming `APPROVED`.

## 6. Chat flow

1. User finds property.
2. User starts chat using `POST /api/v1/chats` with `agent_id` and optional `property_id`.
3. Backend creates or returns existing private chat.
4. User sends text message with `POST /api/v1/chats/{chat_id}/messages`.
5. User sends image/video with `POST /api/v1/chats/{chat_id}/messages/media`.
6. Mobile app connects to `WS /api/v1/ws/chats/{chat_id}?token=<access_token>` for live updates.
7. REST endpoints remain the fallback for unstable mobile connections.

## 7. New API endpoints

### Payments

```txt
POST /api/v1/payments/initialize
GET  /api/v1/payments/verify/{reference}
POST /api/v1/payments/webhook
GET  /api/v1/payments/me
GET  /api/v1/admin/transactions
```

### Chats

```txt
POST  /api/v1/chats
GET   /api/v1/chats
GET   /api/v1/chats/{chat_id}
GET   /api/v1/chats/{chat_id}/messages
POST  /api/v1/chats/{chat_id}/messages
POST  /api/v1/chats/{chat_id}/messages/media
PATCH /api/v1/chats/{chat_id}/read
WS    /api/v1/ws/chats/{chat_id}?token=<access_token>
```

## 8. WebSocket event contract

Client sends:

```json
{
  "type": "message.send",
  "data": {
    "content": "Hello, is this property still available?"
  }
}
```

Server broadcasts:

```json
{
  "type": "message.created",
  "data": {
    "id": "message-id",
    "chat_id": "chat-id",
    "sender_id": "user-id",
    "content": "Hello, is this property still available?",
    "message_type": "TEXT",
    "created_at": "2026-06-15T10:00:00Z"
  }
}
```

For image/video, upload through REST. The server broadcasts the resulting `message.created` event to active WebSocket participants.

## 9. Production notes

- WebSocket connection manager is in-memory. It is fine for one Render instance/MVP.
- For horizontal scaling, use Redis Pub/Sub or a managed realtime layer.
- Do not expose Supabase service role key in mobile app.
- Do not let mobile directly mark payment successful.
- Do not approve an agent from Paystack callback alone; verify from backend or webhook.
