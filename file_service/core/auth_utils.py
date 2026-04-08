"""Authentication helpers for file upload requests."""

import httpx
from fastapi import Header, HTTPException

from core import context
from services.runtime_access import ensure_supabase_configured


def resolve_user_from_access_token(
    token: str,
) -> tuple[str | None, str | None, Exception | None]:
    """Resolve user identity from access token via Supabase SDK then HTTP fallback.
    
    Args:
        token (str): Access token.
    
    Returns:
        tuple[str | None, str | None, Exception | None]: User identity from access token via
                                                         Supabase SDK then HTTP fallback.
    """
    db = ensure_supabase_configured()
    try:
        user_resp = db.auth.get_user(token)
        user_obj = getattr(user_resp, "user", None)
        user_id = getattr(user_obj, "id", None) if user_obj else None
        user_email = getattr(user_obj, "email", None) if user_obj else None
        if user_id:
            return str(user_id), user_email, None
    except Exception as exc:
        first_error = exc
    else:
        first_error = Exception("Access token does not resolve to a user")

    if not context.SUPABASE_URL:
        return None, None, first_error

    headers = {"Authorization": f"Bearer {token}"}
    if context.SUPABASE_KEY:
        headers["apikey"] = context.SUPABASE_KEY

    try:
        response = httpx.get(
            f"{context.SUPABASE_URL.rstrip('/')}/auth/v1/user",
            headers=headers,
            timeout=context.TOKEN_VALIDATION_TIMEOUT_SECONDS,
        )
        if response.status_code == 200:
            payload = response.json()
            user_id = payload.get("id")
            user_email = payload.get("email")
            if user_id:
                return str(user_id), user_email, None
            return None, None, Exception("Supabase /auth/v1/user response has no user id")

        return None, None, Exception(f"Supabase /auth/v1/user returned {response.status_code}")
    except Exception as exc:
        return None, None, exc if str(exc) else first_error


async def verify_internal_request(
    x_user_id: str = Header(None),
    x_user_email: str = Header(None),
    x_access_token: str = Header(None),
):
    """Validate request identity from access token or trusted forwarded headers.
    
    Args:
        x_user_id (str): Identifier for x user.
        x_user_email (str): Parameter x_user_email.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Request identity from access token or trusted forwarded headers.
    """
    ensure_supabase_configured()

    user_id = None
    user_email = None
    token_error = None

    if x_access_token:
        user_id, user_email, token_error = resolve_user_from_access_token(x_access_token)

    if not user_id and x_user_id:
        context.logger.warning(
            "Falling back to gateway identity header for file request authentication"
        )
        user_id = x_user_id
        user_email = x_user_email

    if not user_id:
        if token_error:
            raise HTTPException(status_code=401, detail="Your account cannot be authenticated.")
        raise HTTPException(status_code=401, detail="Unauthorized: missing access token")

    if x_access_token and x_user_id and x_user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden: user mismatch")

    if x_access_token and x_user_email and user_email and x_user_email != user_email:
        raise HTTPException(status_code=403, detail="Forbidden: user mismatch")

    return {"id": user_id, "email": user_email}
