# LLM Service

## Role
AI chat service for the project. Sends prompts to Gemini, stores user history in Supabase, and provides a degraded text fallback if the provider is unavailable.

## Responsibilities
- Generate assistant responses via Gemini.
- Persist prompt and response history in `llm_messages`.
- Normalize provider errors and retry with model fallbacks.
- Serve paginated history and support delete-all.

## Endpoints
- `GET /health`, `GET /metrics`
- `GET /llm/history`
- `DELETE /llm/history`
- `POST /llm/chat`

## Generation flow (algorithm)
1. Build the request payload from the user prompt and runtime config.
2. Try candidate Gemini models in order with retry and backoff.
3. Classify provider errors (credentials, model unavailable, rate limit).
4. If all models fail and degraded fallback is enabled, return a local response.
5. Persist user and assistant messages in `llm_messages` (best effort).

## Dependencies
- Gemini API
- Supabase table `llm_messages`
- Vault for secrets

## Runtime config
- `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_BASE_URL`
- `SUPABASE_URL`, `SUPABASE_KEY`
- `LLM_TIMEOUT_SECONDS`, `LLM_TEMPERATURE`, `LLM_MAX_OUTPUT_TOKENS`
- `LLM_SYSTEM_PROMPT`
- `LLM_PROVIDER_RETRIES`, `LLM_PROVIDER_RETRY_BACKOFF_SECONDS`
- `LLM_DEGRADED_FALLBACK_ENABLED`

## Implementation notes
- History reads are paginated by `limit` and `offset`.
- History deletes return the count of deleted rows.
- Provider failures never block the health endpoint.
