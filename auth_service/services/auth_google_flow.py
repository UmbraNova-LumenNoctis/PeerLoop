"""Google OAuth flow URL builders and fallback policy."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import HTTPException

from core.auth_context import (
    GOOGLE_OAUTH_ALLOW_SUPABASE_FALLBACK,
    GOOGLE_OAUTH_AUTO_FALLBACK,
    POST_CONFIRM_APP_URL,
    SUPABASE_URL,
)
from utils.auth_google_config import is_google_direct_oauth_configured, is_missing_or_placeholder


def build_frontend_login_redirect(
    access_token: str | None = None,
    refresh_token: str | None = None,
    error: str | None = None,
) -> str:
    """Build frontend `/login` redirect URL carrying OAuth fragment values.
    
    Args:
        access_token (str | None): Access token.
        refresh_token (str | None): Refresh token.
        error (str | None): Parameter error.
    
    Returns:
        str: Frontend `/login` redirect URL carrying OAuth fragment values.
    """
    app_url = (POST_CONFIRM_APP_URL or "https://localhost:8443").strip() or "https://localhost:8443"
    parts = urlsplit(app_url)
    scheme = parts.scheme or "http"
    netloc = parts.netloc
    host = (parts.hostname or "").lower()

    if scheme == "https" and host in {"localhost", "127.0.0.1"} and parts.port == 3000:
        scheme = "http"

    path = (parts.path or "").rstrip("/")
    if not path or path == "/":
        path = "/login"
    elif not path.endswith("/login"):
        path = f"{path}/login"

    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    fragment_params: dict[str, str] = {}
    if access_token:
        fragment_params["access_token"] = access_token
    if refresh_token:
        fragment_params["refresh_token"] = refresh_token
    if error:
        fragment_params["error"] = error

    fragment = urlencode(fragment_params, doseq=True)
    return urlunsplit((scheme, netloc, path, urlencode(query, doseq=True), fragment))


def build_supabase_google_authorize_url() -> str:
    """Build Supabase-hosted Google authorization URL for fallback mode.
    
    Returns:
        str: Supabase-hosted Google authorization URL for fallback mode.
    """
    if is_missing_or_placeholder(SUPABASE_URL):
        raise HTTPException(status_code=503, detail="Google OAuth fallback is not configured: missing SUPABASE_URL")

    query = urlencode(
        {
            "provider": "google",
            "redirect_to": build_frontend_login_redirect(),
        }
    )
    return f"{SUPABASE_URL.rstrip('/')}/auth/v1/authorize?{query}"


def should_use_supabase_fallback() -> bool:
    """Return whether fallback OAuth mode should be used.
    
    Returns:
        bool: Whether fallback OAuth mode should be used.
    """
    if is_missing_or_placeholder(SUPABASE_URL):
        return False
    if GOOGLE_OAUTH_ALLOW_SUPABASE_FALLBACK:
        return True
    return GOOGLE_OAUTH_AUTO_FALLBACK and not is_google_direct_oauth_configured()
