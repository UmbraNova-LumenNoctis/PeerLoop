"""Google OAuth configuration helpers."""

from fastapi import HTTPException

from core.auth_context import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URIS,
    REDIRECT_URI,
)


def is_missing_or_placeholder(value: str | None) -> bool:
    """Return ``True`` when a secret/config value is absent or placeholder.
    
    Args:
        value (str | None): Parameter value.
    
    Returns:
        bool: True if missing or placeholder, otherwise False.
    """
    normalized = (value or "").strip()
    if not normalized:
        return True
    return normalized.startswith("REPLACE_ME_")


def parse_google_redirect_candidates() -> list[str]:
    """Build ordered redirect URI candidates from environment settings.
    
    Returns:
        list[str]: Ordered redirect URI candidates from environment settings.
    """
    candidates: list[str] = []
    for raw_uri in [REDIRECT_URI, *GOOGLE_REDIRECT_URIS]:
        uri = (raw_uri or "").strip()
        if uri and uri not in candidates:
            candidates.append(uri)
    return candidates


def resolve_google_redirect_uri() -> str:
    """Resolve the primary redirect URI for direct Google OAuth.
    
    Returns:
        str: Primary redirect URI for direct Google OAuth.
    """
    candidates = parse_google_redirect_candidates()
    if candidates:
        return candidates[0]
    return "https://localhost:8443/auth/google/callback"


def ensure_google_oauth_configured() -> None:
    """Raise HTTP 503 when required direct OAuth settings are missing.
    
    Returns:
        None: None.
    """
    if is_missing_or_placeholder(GOOGLE_CLIENT_ID):
        raise HTTPException(status_code=503, detail="Google OAuth is not configured: invalid GOOGLE_CLIENT_ID")
    if is_missing_or_placeholder(GOOGLE_CLIENT_SECRET):
        raise HTTPException(status_code=503, detail="Google OAuth is not configured: invalid GOOGLE_CLIENT_SECRET")
    if not resolve_google_redirect_uri():
        raise HTTPException(status_code=503, detail="Google OAuth is not configured: missing REDIRECT_URI")


def is_google_direct_oauth_configured() -> bool:
    """Tell whether Google direct OAuth can be used.
    
    Returns:
        bool: True if google direct oauth configured, otherwise False.
    """
    return (
        not is_missing_or_placeholder(GOOGLE_CLIENT_ID)
        and not is_missing_or_placeholder(GOOGLE_CLIENT_SECRET)
        and bool(resolve_google_redirect_uri())
    )
