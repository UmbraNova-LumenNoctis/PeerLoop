"""User and avatar lookup helpers for chat serialization."""

from fastapi import HTTPException
from postgrest.exceptions import APIError

from core.context import require_supabase


def ensure_users_exist(user_ids: list[str]) -> None:
    """Ensure all provided user ids exist in users table.
    
    Args:
        user_ids (list[str]): Identifiers for user.
    
    Returns:
        None: None.
    """
    if not user_ids:
        return

    try:
        users = require_supabase().table("users").select("id").in_("id", user_ids).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"User lookup failed: {exc}") from exc

    found_ids = {str(row.get("id")) for row in (users.data or []) if row.get("id")}
    missing_ids = [user_id for user_id in user_ids if user_id not in found_ids]
    if missing_ids:
        raise HTTPException(status_code=404, detail=f"Users not found: {', '.join(missing_ids)}")


def get_users_map(user_ids: list[str]) -> dict[str, dict]:
    """Load users map keyed by id for a list of user ids.
    
    Args:
        user_ids (list[str]): Identifiers for user.
    
    Returns:
        dict[str, dict]: Retrieved value.
    """
    if not user_ids:
        return {}

    try:
        result = require_supabase().table("users").select("id,pseudo,avatar_id").in_("id", user_ids).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"User lookup failed: {exc}") from exc

    rows = result.data or []
    return {str(row.get("id")): row for row in rows if row.get("id")}


def get_avatar_url_map(avatar_ids: list[str]) -> dict[str, str]:
    """Load avatar URL map keyed by media id.
    
    Args:
        avatar_ids (list[str]): Identifiers for avatar.
    
    Returns:
        dict[str, str]: Retrieved value.
    """
    if not avatar_ids:
        return {}

    try:
        result = require_supabase().table("media_files").select("id,url").in_("id", avatar_ids).execute()
    except APIError:
        return {}

    rows = result.data or []
    return {
        str(row.get("id")): row.get("url")
        for row in rows
        if row.get("id") and row.get("url")
    }
