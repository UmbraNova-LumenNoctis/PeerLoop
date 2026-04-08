# Notification Service

## Role
Stores and serves user notifications. Exposes public routes for the current user and an internal route for other services.

## Responsibilities
- Create notifications on behalf of internal services.
- List notifications with pagination and filters.
- Track read and unread state.
- Provide an unread count for the current user.

## Endpoints
- `GET /health`, `GET /metrics`
- `GET /notifications`
- `GET /notifications/unread-count`
- `POST /notifications/internal`
- `PATCH /notifications/read-all`
- `PATCH /notifications/{notification_id}/read`
- `PATCH /notifications/{notification_id}/unread`
- `DELETE /notifications/{notification_id}`

## Read and write flow (algorithm)
1. Resolve the current user from `x-user-id` or `x-access-token`.
2. List queries support `is_read`, `type`, `limit`, `offset`, and `order` filters.
3. Unread counts are computed with a direct select on `is_read = false`.
4. Internal creation requires `x-internal-service-token` and inserts the row.
5. Updates return the updated row or fall back to a direct fetch.
6. Legacy schemas without `actor_id` are handled by retrying insert without that column.

## Dependencies
- Supabase table `notifications`
- Vault for secrets

## Runtime config
- `SUPABASE_URL`, `SUPABASE_KEY`
- `INTERNAL_SERVICE_TOKEN`

## Implementation notes
- `POST /notifications/internal` is restricted to inter-service calls using `x-internal-service-token`.
- Notifications track `type`, `content`, `source_id`, `actor_id`, `is_read`, and `created_at`.
