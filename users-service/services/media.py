"""Media lookup and profile serialization helpers."""

from fastapi import HTTPException
from postgrest.exceptions import APIError

from core.context import DEFAULT_AVATAR_URL, DEFAULT_COVER_URL, supabase_admin
from schemas.models import UserProfileResponse


def get_media_url(media_id: str | None) -> str | None:
    """Fetch media URL by media id.
    
    Args:
        media_id (str | None): Media identifier.
    
    Returns:
        str | None: Media URL by media id.
    """
    if not media_id:
        return None

    try:
        result = supabase_admin.table("media_files").select("url").eq("id", media_id).limit(1).execute()
    except APIError:
        return None

    rows = result.data or []
    return rows[0].get("url") if rows else None


def validate_media_exists(media_id: str, field_name: str) -> str | None:
    """Ensure media id exists and return its URL.
    
    Args:
        media_id (str): Media identifier.
        field_name (str): Parameter field_name.
    
    Returns:
        str | None: Media id exists and return its URL.
    """
    try:
        media = supabase_admin.table("media_files").select("id,url").eq("id", media_id).limit(1).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"{field_name} lookup failed: {exc}") from exc

    if not media.data:
        raise HTTPException(status_code=404, detail=f"{field_name} media not found")
    return media.data[0].get("url")


def to_profile_response(user_row: dict) -> UserProfileResponse:
    """Build API response model from users row, resolving media URLs.
    
    Args:
        user_row (dict): Parameter user_row.
    
    Returns:
        UserProfileResponse: API response model from users row, resolving media URLs.
    """
    avatar_id = user_row.get("avatar_id")
    cover_id = user_row.get("cover_id")

    avatar_url = get_media_url(str(avatar_id) if avatar_id else None)
    if not avatar_url:
        avatar_url = user_row.get("avatar_url") or DEFAULT_AVATAR_URL

    cover_url = get_media_url(str(cover_id) if cover_id else None)
    if not cover_url:
        cover_url = user_row.get("cover_url") or DEFAULT_COVER_URL

    return UserProfileResponse(
        id=user_row.get("id"),
        pseudo=user_row.get("pseudo"),
        email=user_row.get("email"),
        address=user_row.get("address"),
        bio=user_row.get("bio"),
        avatar_id=avatar_id,
        avatar_url=avatar_url,
        cover_id=cover_id,
        cover_url=cover_url,
        created_at=user_row.get("created_at"),
        updated_at=user_row.get("updated_at"),
    )
