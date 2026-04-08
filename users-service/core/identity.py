"""Identity resolution helpers for users service."""

from typing import Any

from core.context import new_supabase_client


def extract_identity_from_token(x_access_token: str | None) -> tuple[str | None, str | None, dict[str, Any]]:
    """Resolve user id/email/metadata from access token.
    
    Args:
        x_access_token (str | None): Parameter x_access_token.
    
    Returns:
        tuple[str | None, str | None, dict[str, Any]]: User id/email/metadata from access token.
    """
    if not x_access_token:
        return None, None, {}

    try:
        token_client = new_supabase_client()
        user_resp = token_client.auth.get_user(x_access_token)
    except Exception:
        return None, None, {}

    user_obj = getattr(user_resp, "user", None)
    if not user_obj:
        return None, None, {}

    if isinstance(user_obj, dict):
        user_id = user_obj.get("id")
        user_email = user_obj.get("email")
        metadata = user_obj.get("user_metadata")
    else:
        user_id = getattr(user_obj, "id", None)
        user_email = getattr(user_obj, "email", None)
        metadata = getattr(user_obj, "user_metadata", None)

    if not isinstance(metadata, dict):
        metadata = {}

    return (
        str(user_id) if user_id else None,
        str(user_email) if user_email else None,
        metadata,
    )


def resolve_identity(
    x_user_id: str | None,
    x_user_email: str | None,
    x_access_token: str | None,
) -> tuple[str | None, str | None, dict[str, Any]]:
    """Resolve identity from token first, then trusted forwarded headers.
    
    Args:
        x_user_id (str | None): Identifier for x user.
        x_user_email (str | None): Parameter x_user_email.
        x_access_token (str | None): Parameter x_access_token.
    
    Returns:
        tuple[str | None, str | None, dict[str, Any]]: Identity from token first, then trusted
                                                       forwarded headers.
    """
    token_user_id, token_email, token_metadata = extract_identity_from_token(x_access_token)
    if token_user_id:
        return token_user_id, token_email or x_user_email, token_metadata

    if x_user_id:
        return x_user_id, x_user_email, {}

    return None, None, {}
