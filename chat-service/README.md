# Chat Service

## Role
One-to-one messaging service with conversation persistence, realtime presence, and WebSocket delivery for messages and online status.

## Responsibilities
- Create and list conversations.
- Store messages and manage read state.
- Provide presence for conversation participants.
- Emit internal notifications for new conversations and messages.

## Endpoints
- `GET /health`, `GET /metrics`
- `POST /chat/conversations`, `GET /chat/conversations`
- `DELETE /chat/conversations/{conversation_id}`
- `GET /chat/conversations/{conversation_id}/presence`
- `GET /chat/conversations/{conversation_id}/messages`
- `POST /chat/conversations/{conversation_id}/messages`
- `PATCH /chat/conversations/{conversation_id}/read`
- `POST /presence/internal`
- `WS /ws/chat/{conversation_id}`
- `WS /ws/presence`

## Conversation and message flow (algorithm)
1. Direct conversations are deduplicated so a pair does not create multiple active threads.
2. Deleting a conversation is a per-user hide via `hidden_at`.
3. New messages can unhide a previously hidden conversation for all participants.
4. Sending a message writes the row, marks the conversation read for the sender, broadcasts to participants, and emits notifications.

## WebSocket protocol
- Auth token can be provided via `?token=...`, `?access_token=...`, `x-access-token`, or `Authorization: Bearer ...`.
- On connect, the server emits:
- `{"type": "connected", "conversation_id": "...", "user_id": "..."}` or `{ "type": "connected", "scope": "presence", "user_id": "..." }`.
- Chat sockets accept JSON messages with `type`:
- `ping` -> server replies `{"type":"pong"}`.
- `message` -> requires `content`, then broadcasts `{"type":"message","payload":<MessageResponse>}`.
- Presence events are broadcast as `{"type":"presence","event":"join|leave"...}`.
- Errors are returned as `{"type":"error","detail":"..."}`.
- Close codes: `4401` unauthorized, `4403` forbidden, `4404` not found, `1011` server error.

## Dependencies
- Supabase tables `conversations`, `conversation_participants`, `messages`, `users`, `media_files`
- Notification service for internal events
- Vault for secrets

## Runtime config
- `SUPABASE_URL`, `SUPABASE_KEY`
- `NOTIFICATION_SERVICE_URL`, `INTERNAL_SERVICE_TOKEN`
- `INTERNAL_TLS_VERIFY`

## Implementation notes
- `/presence/internal` allows other services to query online users.
- The connection manager tracks sockets per conversation and per user and prunes dead sockets.
