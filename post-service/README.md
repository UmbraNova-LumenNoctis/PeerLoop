# Post Service

## Role
Social post service: create posts, serve feeds, manage likes, and handle comments.

## Responsibilities
- Create, update, and delete posts.
- Serve feeds with pagination and optional filtering.
- Create and remove likes.
- Create, update, and delete comments including threaded replies.
- Emit notifications for social events.

## Endpoints
- `GET /health`, `GET /metrics`
- `POST /posts`, `GET /posts`
- `GET /posts/feed`
- `GET /posts/{post_id}`
- `PATCH /posts/{post_id}`
- `DELETE /posts/{post_id}`
- `POST /posts/{post_id}/like`
- `DELETE /posts/{post_id}/like`
- `GET /posts/{post_id}/comments`
- `POST /posts/{post_id}/comments`
- `PATCH /posts/comments/{comment_id}`
- `DELETE /posts/comments/{comment_id}`

## Feed algorithm
1. Build the author scope from `user_id` and `friend_only` filters.
2. Apply optional `created_before` and `created_after` filters.
3. For `created_at` or `updated_at` sorting, rely on database ordering and pagination.
4. For popularity sorting, fetch a capped window of recent posts, compute engagement (likes + comments), then sort in-memory.
5. Return `has_more` based on the requested `limit` and `offset` window.

## Comment and like behavior
- Likes are idempotent.
- Comment replies are modeled with `parent_comment_id`.
- Deleting a comment can delete an entire thread when needed.

## Dependencies
- Supabase tables `posts`, `comments`, `post_likes`, `friendships`, `users`, `media_files`
- Notification service for social events
- Vault for secrets

## Runtime config
- `SUPABASE_URL`, `SUPABASE_KEY`
- `NOTIFICATION_SERVICE_URL`, `INTERNAL_SERVICE_TOKEN`
- `INTERNAL_TLS_VERIFY`

## Implementation notes
- `friend_only` relies on `accepted` relationships in `friendships`.
- Feed responses include like and comment counts plus `liked_by_me` flags.
