"""User and media storage helpers for post service."""

from fastapi import HTTPException
from postgrest.exceptions import APIError

from core.context import require_supabase


def get_users_map(user_ids: list[str]) -> dict[str, dict]:
    """Fetch users keyed by id with lightweight profile fields.
    
    Args:
        user_ids (list[str]): Identifiers for user.
    
    Returns:
        dict[str, dict]: Users keyed by id with lightweight profile fields.
    """
    if not user_ids:
        return {}

    try:
        result = (
            require_supabase()
            .table("users")
            .select("id,pseudo,avatar_id,avatar_url")
            .in_("id", user_ids)
            .execute()
        )
    except APIError as exc:
        message = str(exc).lower()
        try:
            if "avatar_id" in message and "avatar_url" in message:
                result = require_supabase().table("users").select("id,pseudo").in_("id", user_ids).execute()
            elif "avatar_id" in message:
                result = require_supabase().table("users").select("id,pseudo,avatar_url").in_("id", user_ids).execute()
            elif "avatar_url" in message:
                result = require_supabase().table("users").select("id,pseudo,avatar_id").in_("id", user_ids).execute()
            else:
                raise HTTPException(status_code=502, detail=f"User lookup failed: {exc}") from exc
        except APIError as fallback_exc:
            raise HTTPException(status_code=502, detail=f"User lookup failed: {fallback_exc}") from fallback_exc

    rows = result.data or []
    return {str(row.get("id")): row for row in rows if row.get("id")}


def get_avatar_url_map(avatar_ids: list[str]) -> dict[str, str]:
    """Fetch avatar media urls by media id.
    
    Args:
        avatar_ids (list[str]): Identifiers for avatar.
    
    Returns:
        dict[str, str]: Avatar media urls by media id.
    """
    if not avatar_ids:
        return {}

    try:
        result = require_supabase().table("media_files").select("id,url").in_("id", avatar_ids).execute()
    except APIError:
        return {}

    rows = result.data or []
    return {str(row.get("id")): row.get("url") for row in rows if row.get("id") and row.get("url")}


def get_media_url_map(media_ids: list[str]) -> dict[str, str]:
    """Fetch post media urls by media id.
    
    Args:
        media_ids (list[str]): Identifiers for media.
    
    Returns:
        dict[str, str]: Post media urls by media id.
    """
    if not media_ids:
        return {}

    try:
        result = require_supabase().table("media_files").select("id,url").in_("id", media_ids).execute()
    except APIError:
        return {}

    rows = result.data or []
    return {str(row.get("id")): row.get("url") for row in rows if row.get("id") and row.get("url")}


def get_media_row(media_id: str) -> dict | None:
    """Fetch one media row by id.
    
    Args:
        media_id (str): Media identifier.
    
    Returns:
        dict | None: One media row by id.
    """
    try:
        result = require_supabase().table("media_files").select("id,user_id,url").eq("id", media_id).limit(1).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Media lookup failed: {exc}") from exc

    rows = result.data or []
    return rows[0] if rows else None


def ensure_media_owned_by_user(media_id: str, current_user_id: str) -> None:
    """Validate that a media file exists and belongs to current user.
    
    Args:
        media_id (str): Media identifier.
        current_user_id (str): Identifier for current user.
    
    Returns:
        None: None.
    """
    media = get_media_row(media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    if str(media.get("user_id")) != current_user_id:
        raise HTTPException(status_code=403, detail="You can only attach your own media")
