# Users Service

## Role
Application profile service. Creates the `users` row when missing, exposes the current profile, allows updates, and serves public profile reads by `user_id`.

## Responsibilities
- Ensure a `users` record exists for authenticated users.
- Serve `/user/me` and public profile reads.
- Update editable profile fields with validation.
- Resolve avatar and cover URLs from `media_files` or defaults.

## Endpoints
- `GET /health`, `GET /metrics`
- `GET /user/me`
- `PATCH /user/me`
- `GET /user/{user_id}`

## Profile flow (algorithm)
1. Resolve identity from `x-user-id` headers or access token introspection.
2. Fetch the `users` row; if missing, insert a default profile based on auth metadata.
3. Backfill missing fields (email, avatar, cover) from auth metadata when present.
4. Enforce pseudo uniqueness before applying updates.
5. Resolve `avatar_id` and `cover_id` against `media_files` and fall back to defaults.

## Dependencies
- Supabase tables `users` and `media_files`
- Notification service for profile events
- Vault for secrets
- Prometheus for metrics

## Runtime config
- `SUPABASE_URL`, `SUPABASE_KEY`
- `NOTIFICATION_SERVICE_URL`, `INTERNAL_SERVICE_TOKEN`
- `INTERNAL_TLS_VERIFY`
- `DEFAULT_AVATAR_URL`, `DEFAULT_COVER_URL`

## Implementation notes
- `/user/me` auto-provisions the profile from the auth token when missing.
- The service supports older schemas where media columns may be missing.
- Profile updates can trigger internal notifications for downstream services.
