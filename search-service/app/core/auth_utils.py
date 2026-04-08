"""Authentication helpers for search service routes."""

from fastapi import HTTPException

from .context import new_supabase_client


def resolve_user_id(x_user_id: str | None, x_access_token: str | None) -> str | None:
    """Resolve user id from trusted header or access token.
    
    Args:
        x_user_id (str | None): Identifier for x user.
        x_access_token (str | None): Parameter x_access_token.
    
    Returns:
        str | None: User id from trusted header or access token.
    """
    if x_user_id:
        return x_user_id

    if x_access_token:
        try:
            token_client = new_supabase_client()
            user_resp = token_client.auth.get_user(x_access_token)
            user_obj = getattr(user_resp, "user", None)
            if user_obj and getattr(user_obj, "id", None):
                return str(user_obj.id)
        except Exception:
            return None

    return None


def require_authenticated_user(x_user_id: str | None, x_access_token: str | None) -> str:
    """Return authenticated user id or raise 401.
    
    Args:
        x_user_id (str | None): Identifier for x user.
        x_access_token (str | None): Parameter x_access_token.
    
    Returns:
        str: Authenticated user id or raise 401.
    """
    resolved_user_id = resolve_user_id(x_user_id, x_access_token)
    if not resolved_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: missing or invalid access token")
    return resolved_user_id
