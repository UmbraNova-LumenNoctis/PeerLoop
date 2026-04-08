"""Identity and profile lookup helpers for user router."""

from typing import Any

from core.user_context import PROFILE_SELECT_COLUMNS, supabase


def select_user_profile_by_id(user_id: str) -> dict[str, Any] | None:
    """Fetch public profile row by user id.
    
    Args:
        user_id (str): User identifier.
    
    Returns:
        dict[str, Any] | None: Public profile row by user id.
    """
    try:
        result = (
            supabase.table("users")
            .select(PROFILE_SELECT_COLUMNS)
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
    except Exception:
        return None

    rows = result.data or []
    return rows[0] if rows else None


def build_fallback_pseudo(email: str | None, user_metadata: dict[str, Any]) -> str | None:
    """Build pseudo fallback from metadata or email prefix.
    
    Args:
        email (str | None): Parameter email.
        user_metadata (dict[str, Any]): Parameter user_metadata.
    
    Returns:
        str | None: Pseudo fallback from metadata or email prefix.
    """
    candidate = user_metadata.get("username") or user_metadata.get("full_name") or user_metadata.get("name")
    if not isinstance(candidate, str) or not candidate.strip():
        candidate = email.split("@")[0] if isinstance(email, str) and "@" in email else None

    if not candidate:
        return None
    return candidate.strip()[:30]


def extract_identity_from_token(token: str) -> tuple[str | None, str | None, dict[str, Any]]:
    """Resolve user identity from access token.
    
    Args:
        token (str): Access token.
    
    Returns:
        tuple[str | None, str | None, dict[str, Any]]: User identity from access token.
    """
    try:
        user_resp = supabase.auth.get_user(token)
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
    """Resolve identity from forwarded headers or token fallback.
    
    Args:
        x_user_id (str | None): Identifier for x user.
        x_user_email (str | None): Parameter x_user_email.
        x_access_token (str | None): Parameter x_access_token.
    
    Returns:
        tuple[str | None, str | None, dict[str, Any]]: Identity from forwarded headers or token
                                                       fallback.
    """
    if x_user_id and x_user_email:
        return x_user_id, x_user_email, {}

    if x_access_token:
        token_user_id, token_email, token_metadata = extract_identity_from_token(x_access_token)
        if token_user_id:
            return token_user_id, token_email, token_metadata

    return None, None, {}
