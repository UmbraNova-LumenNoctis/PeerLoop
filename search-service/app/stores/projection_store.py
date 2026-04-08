"""Projection and aggregate storage helpers for search endpoints."""

from collections import defaultdict

from fastapi import HTTPException
from postgrest.exceptions import APIError

from ..core.context import require_supabase


def get_users_map(user_ids: list[str]) -> dict[str, dict]:
    """Fetch users projection keyed by id.
    
    Args:
        user_ids (list[str]): Identifiers for user.
    
    Returns:
        dict[str, dict]: Users projection keyed by id.
    """
    if not user_ids:
        return {}

    deduped_ids = sorted({user_id for user_id in user_ids if user_id})
    if not deduped_ids:
        return {}

    try:
        result = require_supabase().table("users").select("id,pseudo,email,bio,avatar_id").in_("id", deduped_ids).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"User lookup failed: {exc}") from exc

    rows = result.data or []
    return {str(row.get("id")): row for row in rows if row.get("id")}


def get_avatar_url_map(avatar_ids: list[str]) -> dict[str, str]:
    """Fetch avatar media URLs keyed by media id.
    
    Args:
        avatar_ids (list[str]): Identifiers for avatar.
    
    Returns:
        dict[str, str]: Avatar media URLs keyed by media id.
    """
    if not avatar_ids:
        return {}

    deduped_ids = sorted({avatar_id for avatar_id in avatar_ids if avatar_id})
    if not deduped_ids:
        return {}

    try:
        result = require_supabase().table("media_files").select("id,url").in_("id", deduped_ids).execute()
    except APIError:
        return {}

    rows = result.data or []
    return {str(row.get("id")): row.get("url") for row in rows if row.get("id") and row.get("url")}


def get_media_url_map(media_ids: list[str]) -> dict[str, str]:
    """Fetch post media URLs keyed by media id.
    
    Args:
        media_ids (list[str]): Identifiers for media.
    
    Returns:
        dict[str, str]: Post media URLs keyed by media id.
    """
    if not media_ids:
        return {}

    deduped_ids = sorted({media_id for media_id in media_ids if media_id})
    if not deduped_ids:
        return {}

    try:
        result = require_supabase().table("media_files").select("id,url").in_("id", deduped_ids).execute()
    except APIError:
        return {}

    rows = result.data or []
    return {str(row.get("id")): row.get("url") for row in rows if row.get("id") and row.get("url")}


def get_post_stats(post_ids: list[str], current_user_id: str) -> tuple[dict[str, int], dict[str, int], set[str]]:
    """Return likes count, comments count and liked-by-me set for posts.
    
    Args:
        post_ids (list[str]): Identifiers for post.
        current_user_id (str): Identifier for current user.
    
    Returns:
        tuple[dict[str, int], dict[str, int], set[str]]: Likes count, comments count and liked-by-me
                                                         set for posts.
    """
    like_count_map: dict[str, int] = defaultdict(int)
    comment_count_map: dict[str, int] = defaultdict(int)
    liked_post_ids: set[str] = set()

    if not post_ids:
        return like_count_map, comment_count_map, liked_post_ids

    try:
        likes = require_supabase().table("post_likes").select("post_id").in_("post_id", post_ids).execute()
        comments = require_supabase().table("comments").select("post_id").in_("post_id", post_ids).execute()
        my_likes = (
            require_supabase()
            .table("post_likes")
            .select("post_id")
            .eq("user_id", current_user_id)
            .in_("post_id", post_ids)
            .execute()
        )
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Post stats lookup failed: {exc}") from exc

    for row in likes.data or []:
        post_id = row.get("post_id")
        if post_id:
            like_count_map[str(post_id)] += 1

    for row in comments.data or []:
        post_id = row.get("post_id")
        if post_id:
            comment_count_map[str(post_id)] += 1

    for row in my_likes.data or []:
        post_id = row.get("post_id")
        if post_id:
            liked_post_ids.add(str(post_id))

    return like_count_map, comment_count_map, liked_post_ids
