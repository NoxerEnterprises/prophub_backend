# ProHub API — Agent Access & Geographic Group Chat

Base prefix: `/api/v1`

Authentication: `Authorization: Bearer <access_token>` unless stated otherwise.

## 1. Agent access model

An approved agent has full agent functionality when either of these access states is valid and unexpired:

- `ACTIVE` — paid Paystack subscription.
- `ADMIN_GRANTED` — access manually granted by an admin.

`ADMIN_GRANTED` defaults to 12 months. `REVOKED`, `INACTIVE`, `EXPIRED`, and `CANCELLED` do not provide agent access.

Full agent access requires all of the following:

- email verified;
- agent status `APPROVED`;
- NIN document `APPROVED`;
- access status `ACTIVE` or `ADMIN_GRANTED`;
- `subscription_expires_at` is in the future.

A revoked agent can log in and subscribe again, but cannot create/update listings or use chat until access is restored.

### Approve agent with payment override

`PATCH /admin/agents/{agent_id}/approve`

```json
{
  "allow_override": true,
  "note": "Approved with complimentary access"
}
```

When `allow_override=true` and the agent has no active paid access, approval grants `ADMIN_GRANTED` access for 12 months automatically. NIN approval is still mandatory; the override does not bypass identity review.

### Manually grant access

`PATCH /admin/agents/{agent_id}/grant-access`

```json
{
  "duration_months": 12,
  "note": "Complimentary access"
}
```

`duration_months` accepts `1` through `12` and defaults to `12` in the request model.

Result: agent remains `APPROVED`; `subscription_status=ADMIN_GRANTED`; start and expiry dates are set.

### Revoke agent access

`PATCH /admin/agents/{agent_id}/revoke-access`

```json
{
  "note": "Subscription/access revoked by Noxer"
}
```

Result: agent remains `APPROVED`, but `subscription_status=REVOKED`. The agent loses agent-only functionality immediately, including chat. A successful new Paystack subscription restores `ACTIVE` access automatically.

### Step down agent

`PATCH /admin/agents/{agent_id}/step-down`

```json
{
  "note": "Agent requires re-review"
}
```

Result:

- agent status becomes `PENDING`;
- access becomes `REVOKED`;
- existing approval is cleared;
- agent must subscribe again and be approved again before regaining agent functionality.

## 2. Geographic agent group chats

Group chats reuse the existing chat tables and WebSocket endpoint. Only approved agents with valid `ACTIVE` or `ADMIN_GRANTED` access can create, discover, join, read, or send messages in agent groups.

### Create geographic group

`POST /chats/groups`

```json
{
  "title": "Lekki Phase 1 Agents",
  "description": "Agent collaboration for listings in Lekki Phase 1",
  "country": "Nigeria",
  "state": "Lagos",
  "local_government": "Eti-Osa",
  "community": "Lekki Phase 1"
}
```

`state` and `title` are required. `country` defaults to `Nigeria`. Local government and community are optional and allow narrower groups.

The creator joins automatically with role `OWNER`.

### Discover geographic groups

`GET /chats/groups`

Optional query parameters:

`country`, `state`, `local_government`, `community`, `page`, `limit`

Example:

`GET /api/v1/chats/groups?state=Lagos&local_government=Eti-Osa&page=1&limit=20`

Each result includes `participant_count` and `is_member`.

### Join group

`POST /chats/groups/{chat_id}/join`

No body required.

### Leave group

`POST /chats/groups/{chat_id}/leave`

No body required. The current `OWNER` cannot leave until ownership-transfer functionality is added.

### Group text/media messages

Existing endpoints are reused:

- `POST /chats/{chat_id}/messages` — text.
- `POST /chats/{chat_id}/messages/media` — image/video.
- `GET /chats/{chat_id}/messages` — history.
- `PATCH /chats/{chat_id}/read` — read state.

### Share an existing property listing

`POST /chats/{chat_id}/messages/listing`

```json
{
  "property_id": "PROPERTY_UUID",
  "caption": "New 4-bedroom duplex available",
  "client_message_id": "mobile-generated-uuid"
}
```

Rules:

- group chat only;
- sender must own the property;
- property must be published and not hidden/deleted;
- property location must match every geographic field configured on the group.

The returned message has `message_type="LISTING"`, `shared_property_id`, and `shared_property` summary data.

## 3. WebSocket

The existing endpoint is reused for both private and group chats:

`WS /api/v1/ws/chats/{chat_id}?token=<access_token>`

Text event:

```json
{
  "type": "message.send",
  "data": {
    "content": "Hello everyone",
    "client_message_id": "mobile-generated-uuid"
  }
}
```

The server broadcasts `message.created`. Listing shares are created over REST and are also broadcast as `message.created` events to connected group participants.

Revoked or stepped-down agents are rejected from REST chat endpoints and the WebSocket connection.

## 4. Email OTP compatibility fix

`POST /auth/verify-email` continues to use:

```json
{
  "email": "user@example.com",
  "otp_code": "123456"
}
```

For frontend compatibility, the backend also accepts `otp` or `code` as aliases for `otp_code`.
