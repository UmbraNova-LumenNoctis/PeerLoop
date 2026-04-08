# Friendship Service

## Role
Manage social relationships: request, accept, block, delete, and enrich responses with profile, avatar, and online status.

## Responsibilities
- Create and manage friendship requests.
- Resolve target users by UUID or pseudo.
- Enrich responses with profile data and presence status.
- Emit internal notifications for social events.

## Endpoints
- `GET /health`, `GET /metrics`
- `POST /friendships/request`
- `GET /friendships`
- `GET /friendships/pending`
- `GET /friendships/incoming`
- `GET /friendships/outgoing`
- `PATCH /friendships/{friendship_id}/accept`
- `PATCH /friendships/{friendship_id}/block`
- `DELETE /friendships/{friendship_id}`

## Relationship flow (algorithm)
1. Resolve the target user by UUID or pseudo.
2. Check for an existing friendship in either direction.
3. Create the request if none exists, or return the existing row.
4. Listing merges rows where the user is `user_a_id` or `user_b_id`, then dedupes and sorts.
5. Status updates use delete + insert to avoid a stale `updated_at` trigger.

## Dependencies
- Supabase tables `friendships`, `users`, `media_files`
- Chat service for internal presence
- Notification service for social events
- Vault for secrets

## Runtime config
- `SUPABASE_URL`, `SUPABASE_KEY`
- `CHAT_SERVICE_URL`
- `NOTIFICATION_SERVICE_URL`, `INTERNAL_SERVICE_TOKEN`
- `INTERNAL_TLS_VERIFY`

## Implementation notes
- Target users can be resolved by UUID or pseudo, depending on the route.
- Responses include `friend_user_id`, `friend_pseudo`, `friend_avatar_url`, `friend_online`, and direction.
- Business statuses are `pending`, `accepted`, and `blocked`.
