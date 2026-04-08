"""Session and refresh-cookie helpers for auth workflows."""

from typing import Any

from fastapi import Response

from core.auth_context import (
    AUTH_COOKIE_DOMAIN,
    AUTH_COOKIE_SAMESITE,
    AUTH_COOKIE_SECURE,
    REFRESH_COOKIE_MAX_AGE,
    REFRESH_TOKEN_COOKIE_NAME,
)


def extract_session(auth_response: Any) -> Any:
    """Extract session object from Supabase SDK response.
    
    Args:
        auth_response (Any): Parameter auth_response.
    
    Returns:
        Any: Session object from Supabase SDK response.
    """
    if auth_response is None:
        return None
    if isinstance(auth_response, dict):
        return auth_response.get("session") or (auth_response.get("data") or {}).get("session")
    return getattr(auth_response, "session", None)


def extract_auth_user(auth_response: Any) -> Any:
    """Extract authenticated user object from Supabase SDK response.
    
    Args:
        auth_response (Any): Parameter auth_response.
    
    Returns:
        Any: Authenticated user object from Supabase SDK response.
    """
    if auth_response is None:
        return None
    if isinstance(auth_response, dict):
        return auth_response.get("user") or (auth_response.get("data") or {}).get("user")
    return getattr(auth_response, "user", None)


def session_value(session: Any, key: str) -> Any:
    """Read one session attribute from dict/object session payload.
    
    Args:
        session (Any): Client session instance.
        key (str): Parameter key.
    
    Returns:
        Any: Result of the operation.
    """
    if session is None:
        return None
    if isinstance(session, dict):
        return session.get(key)
    return getattr(session, key, None)


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Persist refresh token in secure HttpOnly cookie.
    
    Args:
        response (Response): FastAPI response object to mutate.
        refresh_token (str): Refresh token.
    
    Returns:
        None: None.
    """
    token = (refresh_token or "").strip()
    if not token:
        return

    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=token,
        max_age=REFRESH_COOKIE_MAX_AGE,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite=AUTH_COOKIE_SAMESITE,
        path="/",
        domain=AUTH_COOKIE_DOMAIN,
    )


def clear_refresh_cookie(response: Response) -> None:
    """Delete refresh token cookie from response.
    
    Args:
        response (Response): FastAPI response object to mutate.
    
    Returns:
        None: None.
    """
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        path="/",
        domain=AUTH_COOKIE_DOMAIN,
        secure=AUTH_COOKIE_SECURE,
        samesite=AUTH_COOKIE_SAMESITE,
    )
