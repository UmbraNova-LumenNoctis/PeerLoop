"""Shared configuration and models for auth router modules."""

import os

from pydantic import BaseModel, constr
from supabase import create_client
from supabase.lib.client_options import ClientOptions

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = (os.getenv("REDIRECT_URI") or "").strip()
GOOGLE_REDIRECT_URIS = [
    item.strip()
    for item in (os.getenv("GOOGLE_REDIRECT_URIS") or "").split(",")
    if item.strip()
]
EMAIL_CONFIRM_REDIRECT_URL = os.getenv("EMAIL_CONFIRM_REDIRECT_URL")
POST_CONFIRM_APP_URL = os.getenv("POST_CONFIRM_APP_URL")
GOOGLE_OAUTH_ALLOW_SUPABASE_FALLBACK = (
    os.getenv("GOOGLE_OAUTH_ALLOW_SUPABASE_FALLBACK", "").strip().lower()
    in {"1", "true", "yes", "on"}
)
GOOGLE_OAUTH_AUTO_FALLBACK = (
    os.getenv("GOOGLE_OAUTH_AUTO_FALLBACK", "").strip().lower()
    in {"1", "true", "yes", "on"}
)
AUTH_STRICT_EMAIL_LINKING = (
    os.getenv("AUTH_STRICT_EMAIL_LINKING", "").strip().lower()
    in {"1", "true", "yes", "on"}
)
GOOGLE_REQUIRE_VERIFIED_EMAIL = (
    os.getenv("GOOGLE_REQUIRE_VERIFIED_EMAIL", "").strip().lower()
    in {"1", "true", "yes", "on"}
)
REFRESH_TOKEN_COOKIE_NAME = os.getenv("REFRESH_TOKEN_COOKIE_NAME", "").strip()
AUTH_COOKIE_DOMAIN = os.getenv("AUTH_COOKIE_DOMAIN") or None
AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
AUTH_COOKIE_SAMESITE = (os.getenv("AUTH_COOKIE_SAMESITE") or "").strip().lower()
if AUTH_COOKIE_SAMESITE not in {"lax", "strict", "none"}:
    AUTH_COOKIE_SAMESITE = "none"
REFRESH_COOKIE_MAX_AGE = int(os.getenv("REFRESH_COOKIE_MAX_AGE", "2592000"))
PENDING_LOGIN_2FA_TTL_SECONDS = int(os.getenv("PENDING_LOGIN_2FA_TTL_SECONDS", "300"))


def new_supabase_client():
    """Create a non-persistent Supabase client.
    
    Returns:
        Any: Non-persistent Supabase client.
    """
    return create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
        options=ClientOptions(auto_refresh_token=False, persist_session=False),
    )


supabase = new_supabase_client()


class SessionExchangeRequest(BaseModel):
    """Callback session payload from frontend."""

    access_token: str
    refresh_token: str


class RefreshRequest(BaseModel):
    """Optional explicit refresh payload."""

    refresh_token: str | None = None


class Login2FAVerifyRequest(BaseModel):
    """Pending 2FA challenge verification request."""

    challenge_id: constr(min_length=8)
    code: constr(min_length=6, max_length=6)
