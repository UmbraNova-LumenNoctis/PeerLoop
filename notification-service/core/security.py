"""Authentication and internal token helpers for notification service."""

from core.context import INTERNAL_SERVICE_TOKEN, require_supabase


def resolve_user_id(x_user_id: str | None, x_access_token: str | None) -> str | None:
    """Resolve current user id from forwarded id header or access token.
    
    Args:
        x_user_id (str | None): Identifier for x user.
        x_access_token (str | None): Parameter x_access_token.
    
    Returns:
        str | None: Current user id from forwarded id header or access token.
    """
    if x_user_id:
        return x_user_id

    if x_access_token:
        try:
            user_resp = require_supabase().auth.get_user(x_access_token)
            user_obj = getattr(user_resp, "user", None)
            if user_obj and getattr(user_obj, "id", None):
                return str(user_obj.id)
        except Exception:
            return None

    return None


def is_internal_token_valid(x_internal_service_token: str | None) -> bool:
    """Validate internal service token for trusted cross-service endpoints.
    
    Args:
        x_internal_service_token (str | None): Parameter x_internal_service_token.
    
    Returns:
        bool: True if internal token valid, otherwise False.
    """
    if not INTERNAL_SERVICE_TOKEN:
        return False
    return bool(x_internal_service_token and x_internal_service_token == INTERNAL_SERVICE_TOKEN)
