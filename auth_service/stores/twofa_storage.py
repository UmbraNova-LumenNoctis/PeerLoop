"""Storage helpers for 2FA data and metadata."""

from fastapi import HTTPException
from postgrest.exceptions import APIError

from core.twofa_context import supabase_admin
from utils.twofa_helpers import extract_totp_secret, is_missing_column_error


def get_auth_user_metadata(user_id: str) -> dict:
    """Fetch user_metadata from Supabase Auth admin API.
    
    Args:
        user_id (str): User identifier.
    
    Returns:
        dict: User_metadata from Supabase Auth admin API.
    """
    try:
        user_resp = supabase_admin.auth.admin.get_user_by_id(user_id)
        auth_user = getattr(user_resp, "user", None)
        metadata = getattr(auth_user, "user_metadata", None) if auth_user else None
        return dict(metadata or {})
    except Exception:
        return {}


def update_auth_user_metadata(user_id: str, updates: dict) -> None:
    """Merge 2FA-related keys into Supabase Auth user metadata.
    
    Args:
        user_id (str): User identifier.
        updates (dict): Parameter updates.
    
    Returns:
        None: None.
    """
    try:
        supabase_admin.auth.admin.update_user_by_id(user_id, {"user_metadata": updates})
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"2FA metadata update failed: {exc}") from exc


def get_secret_from_metadata(user_id: str) -> str | None:
    """Extract TOTP secret from auth metadata.
    
    Args:
        user_id (str): User identifier.
    
    Returns:
        str | None: TOTP secret from auth metadata.
    """
    metadata = get_auth_user_metadata(user_id)
    return extract_totp_secret(metadata)


def load_user_profile(user_id: str) -> dict:
    """Load one user profile row from ``users`` table.
    
    Args:
        user_id (str): User identifier.
    
    Returns:
        dict: Retrieved value.
    """
    try:
        user = supabase_admin.table("users").select("*").eq("id", user_id).single().execute().data
        return dict(user or {})
    except APIError:
        return {}


def safe_update_user_columns(user_id: str, updates: dict) -> bool:
    """Try updating user columns one by one while tolerating missing legacy columns.
    
    Args:
        user_id (str): User identifier.
        updates (dict): Parameter updates.
    
    Returns:
        bool: Result of the operation.
    """
    persisted = False
    for column, value in updates.items():
        try:
            supabase_admin.table("users").update({column: value}).eq("id", user_id).execute()
            persisted = True
        except APIError as exc:
            if is_missing_column_error(exc, column):
                continue
            raise HTTPException(status_code=502, detail=f"2FA storage update failed: {exc}") from exc
    return persisted
