"""Identity lookup helpers backed by users/auth tables."""

from core.auth_context import supabase
from utils.auth_token_utils import extract_auth_metadata


def get_user_by_id(user_id: str) -> dict:
    """Fetch one user profile row by identifier.
    
    Args:
        user_id (str): User identifier.
    
    Returns:
        dict: One user profile row by identifier.
    """
    try:
        user = supabase.table("users").select("*").eq("id", user_id).single().execute().data
        return dict(user or {})
    except Exception:
        return {}


def get_auth_user_metadata_by_id(user_id: str) -> dict:
    """Fetch Supabase auth user metadata by identifier.
    
    Args:
        user_id (str): User identifier.
    
    Returns:
        dict: Supabase auth user metadata by identifier.
    """
    auth_admin = getattr(getattr(supabase, "auth", None), "admin", None)
    if not auth_admin:
        return {}
    try:
        user_resp = auth_admin.get_user_by_id(user_id)
        auth_user = getattr(user_resp, "user", None)
        return extract_auth_metadata(auth_user)
    except Exception:
        return {}
