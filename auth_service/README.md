# Auth Service

## Role
Authentication service for the platform. Handles signup, login, email confirmation, refresh via HttpOnly cookie, Google OAuth, TOTP 2FA, and access to the authenticated profile.

## Responsibilities
- Create Supabase Auth users and provision the `users` table.
- Authenticate by email or username (pseudo).
- Issue access tokens and refresh cookies.
- Manage 2FA enrollment, verification, and disable.
- Handle Google OAuth direct and fallback flows.

## Endpoints
- `GET /health`, `GET /metrics`
- `POST /auth/register`
- `GET /auth/email/confirm`
- `POST /auth/login`
- `POST /auth/login/2fa/verify`
- `POST /auth/session/exchange`
- `POST /auth/refresh`
- `GET /auth/login/google`
- `GET /auth/google/callback`
- `GET /2fa/status`
- `POST /2fa/enable`
- `POST /2fa/verify`
- `POST /2fa/disable`
- `GET /user/me`
- `GET /user/{user_id}`

## Auth flows (algorithm)
1. Signup creates a Supabase Auth user, then inserts a matching row in `public.users`.
2. Login accepts email or pseudo, resolves to email, then authenticates with Supabase.
3. If 2FA is enabled, login returns `202` with a `challenge_id` and defers session issuance.
4. 2FA verification checks the TOTP code and finalizes the session and refresh cookie.
5. Refresh exchanges the refresh token for new access credentials and updates the cookie.
6. Google OAuth can run in direct mode or fall back to Supabase-hosted OAuth as configured.

## 2FA behavior
- TOTP secrets are stored in user profile columns and Supabase auth metadata.
- Pending 2FA challenges are stored in-memory with a TTL and are not shared across instances.

## Dependencies
- Supabase Auth and `public.users`
- Google OAuth
- `pyotp` and `qrcode` for TOTP setup
- Vault for secrets
- Prometheus for metrics

## Runtime config
- `SUPABASE_URL`, `SUPABASE_KEY`
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- `REDIRECT_URI`, `GOOGLE_REDIRECT_URIS`
- `EMAIL_CONFIRM_REDIRECT_URL`, `POST_CONFIRM_APP_URL`
- `REFRESH_TOKEN_COOKIE_NAME`, `REFRESH_COOKIE_MAX_AGE`
- `AUTH_COOKIE_DOMAIN`, `AUTH_COOKIE_SECURE`, `AUTH_COOKIE_SAMESITE`
- `PENDING_LOGIN_2FA_TTL_SECONDS`
- `GOOGLE_OAUTH_ALLOW_SUPABASE_FALLBACK`, `GOOGLE_OAUTH_AUTO_FALLBACK`
- `AUTH_STRICT_EMAIL_LINKING`, `GOOGLE_REQUIRE_VERIFIED_EMAIL`

## Implementation notes
- Login uses a memory-backed 2FA challenge store keyed by `challenge_id`.
- Session cookies are set and cleared by the service to keep refresh logic centralized.
- Profile data can be resynced when OAuth flows complete.
