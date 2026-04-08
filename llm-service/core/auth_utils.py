"""Authentication helpers for llm routes."""

from core.context import supabase_admin


def resolve_user_id(x_user_id: str | None, x_access_token: str | None) -> str | None:
    """Resolve user id from forwarded user header or access token.
    
    Args:
        x_user_id (str | None): Identifier for x user.
        x_access_token (str | None): Parameter x_access_token.
    
    Returns:
        str | None: User id from forwarded user header or access token.
    """
    if x_user_id:
        return x_user_id

    if x_access_token and supabase_admin:
        try:
            user_resp = supabase_admin.auth.get_user(x_access_token)
            user_obj = getattr(user_resp, "user", None)
            if user_obj and getattr(user_obj, "id", None):
                return str(user_obj.id)
        except Exception:
            return None

    return None
