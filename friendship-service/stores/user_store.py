"""User and avatar storage helpers for friendship service."""

from fastapi import HTTPException
from postgrest.exceptions import APIError

from core.context import require_supabase
from schemas.models import FriendshipCreateRequest


def get_user_by_id(user_id: str) -> dict | None:
    """Fetch one user projection by id.
    
    Args:
        user_id (str): User identifier.
    
    Returns:
        dict | None: One user projection by id.
    """
    try:
        result = require_supabase().table("users").select("id,pseudo,avatar_id").eq("id", user_id).limit(1).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"User lookup failed: {exc}") from exc
    rows = result.data or []
    return rows[0] if rows else None


def get_user_by_pseudo(pseudo: str) -> dict | None:
    """Fetch one user projection by pseudo.
    
    Args:
        pseudo (str): Parameter pseudo.
    
    Returns:
        dict | None: One user projection by pseudo.
    """
    try:
        result = require_supabase().table("users").select("id,pseudo,avatar_id").eq("pseudo", pseudo).limit(1).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"User lookup failed: {exc}") from exc
    rows = result.data or []
    return rows[0] if rows else None


def resolve_target_user(payload: FriendshipCreateRequest) -> dict:
    """Resolve friendship target user from id or pseudo payload fields.
    
    Args:
        payload (FriendshipCreateRequest): Parsed request payload.
    
    Returns:
        dict: Friendship target user from id or pseudo payload fields.
    """
    if payload.target_user_id is not None:
        user = get_user_by_id(str(payload.target_user_id))
        if not user:
            raise HTTPException(status_code=404, detail="Target user not found")
        return user

    pseudo = (payload.target_pseudo or "").strip()
    user = get_user_by_pseudo(pseudo)
    if not user:
        raise HTTPException(status_code=404, detail="Target user not found")
    return user


def get_users_map(user_ids: list[str]) -> dict[str, dict]:
    """Fetch users map keyed by user id.
    
    Args:
        user_ids (list[str]): Identifiers for user.
    
    Returns:
        dict[str, dict]: Users map keyed by user id.
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
    """Fetch avatar media urls keyed by media id.
    
    Args:
        avatar_ids (list[str]): Identifiers for avatar.
    
    Returns:
        dict[str, str]: Avatar media urls keyed by media id.
    """
    if not avatar_ids:
        return {}

    try:
        result = require_supabase().table("media_files").select("id,url").in_("id", avatar_ids).execute()
    except APIError:
        return {}

    rows = result.data or []
    return {str(row.get("id")): row.get("url") for row in rows if row.get("id") and row.get("url")}
