# API Gateway

## Role
Public HTTP entrypoint behind Nginx. It validates bearer tokens, resolves user identity via Supabase, injects identity headers for internal services, and proxies business routes. It also exposes health and Prometheus metrics.

## Responsibilities
- Handle CORS for browser clients.
- Validate JWTs and propagate identity headers to upstream services.
- Normalize headers by removing hop-by-hop values before proxying.
- Proxy requests to internal services and pass through upstream responses.
- Build public base URLs for documentation and WebSocket links.

## Request flow (algorithm)
1. Sanitize headers by removing hop-by-hop and gateway-controlled keys.
2. Extract the bearer token and call Supabase `/auth/v1/user` when possible to resolve identity.
3. Inject `x-access-token` and optional `x-user-id`/`x-user-email` headers.
4. Forward the request to the selected upstream service with `httpx`.
5. Map the upstream response: JSON stays JSON, non-JSON payloads are returned as-is.
6. Record request count and duration in Prometheus middleware.

## WebSocket support
- The gateway does not terminate WebSocket traffic; chat sockets are served by the chat service.
- Helper endpoints build authenticated WS URLs using forwarded headers:
- `GET /api/chat/ws-url/{conversation_id}`
- `GET /api/chat/presence-ws-url`
- The response includes a `ws_url` with `?token=...` and alternative header-based auth templates.

## Exposed routes
- `GET /`, `GET /health`, `GET /metrics`
- Auth and identity proxy: `/api/auth/*`, `/api/2fa/*`, `/api/user/*`
- Social proxy: `/api/posts/*`, `/api/friendships/*`, `/api/notifications/*`
- Media and search proxy: `/api/files/upload`, `/api/search/*`
- Chat and AI proxy: `/api/chat/*`, `/api/llm/*`

## Upstream services
- `auth_service`
- `users_service`
- `file_service`
- `friendship_service`
- `post_service`
- `notification_service`
- `chat_service`
- `llm_service`
- `search_service`

## Runtime config
- `SUPABASE_URL`, `SUPABASE_KEY`
- `VAULT_ADDR`, `VAULT_TOKEN`, `INTERNAL_TLS_VERIFY`
- `CORS_ALLOW_ORIGINS`, `ENVIRONMENT`
- `AUTH_SERVICE_URL`, `USER_SERVICE_URL`, `FILE_SERVICE_URL`
- `FRIENDSHIP_SERVICE_URL`, `POST_SERVICE_URL`, `NOTIFICATION_SERVICE_URL`
- `CHAT_SERVICE_URL`, `LLM_SERVICE_URL`, `SEARCH_SERVICE_URL`

## Observability
- `GET /metrics` exposes Prometheus counters and histograms for request count and latency.
