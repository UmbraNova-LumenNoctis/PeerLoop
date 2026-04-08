# Search Service

## Role
Search for users and posts. The active implementation queries Supabase directly and applies fuzzy scoring in the service.

## Responsibilities
- Fuzzy search over user identity fields and post content.
- Rank and paginate results.
- Enrich responses with media URLs and engagement counts.
- Resolve current user identity for `liked_by_me` flags.

## Endpoints
- `GET /`
- `GET /health`
- `GET /metrics`
- `GET /search/users`
- `GET /search/posts`

## Scoring algorithm
- Text is normalized to lowercase and trimmed.
- Token overlap and character n-grams are computed.
- Jaccard similarity on n-grams provides a fuzzy signal.
- Exact match and prefix signals boost the score.
- Final fuzzy similarity blends token overlap and n-gram similarity.

## User search flow (algorithm)
1. Fetch candidates with `ILIKE` on `pseudo`, `email`, and `bio`.
2. Deduplicate by user id across the three candidate sets.
3. Score users with weighted fields: pseudo (0.62), email (0.24), bio (0.14).
4. Apply a small bonus for exact pseudo matches.
5. Filter low scores, then sort by score and deterministic tie-breakers.
6. Enrich with avatar URLs from `media_files` or defaults.

## Post search flow (algorithm)
1. Fetch candidates by post `content` and by matching author profiles.
2. Deduplicate by post id across candidate sources.
3. Score posts using content relevance, author match, and a recency boost.
4. Filter low scores, then paginate the ranked list.
5. Enrich with media URLs, author avatars, and engagement counts.

## Dependencies
- Supabase tables `users`, `posts`, `media_files`, `post_likes`, `comments`
- Vault for secrets
- Prometheus for metrics

## Runtime config
- `SUPABASE_URL`, `SUPABASE_KEY`
- `DEFAULT_AVATAR_URL`

## Implementation notes
- `/search/posts` uses `limit` and `offset` for pagination after ranking.
- `liked_by_me` is computed from `post_likes` for the current user.
- Auth identity is resolved via `x-user-id` or introspection of `x-access-token`.
- Legacy Meilisearch/SQLAlchemy files exist under `app/` but are not used by `app/main.py`.
