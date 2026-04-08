"""Like and aggregate engagement storage helpers."""

from collections import defaultdict

from fastapi import HTTPException
from postgrest.exceptions import APIError

from core.context import require_supabase


def get_post_like_and_comment_stats(post_ids: list[str], current_user_id: str) -> tuple[dict[str, int], dict[str, int], set[str]]:
    """Return likes count, comments count, and liked-by-me flags by post id.
    
    Args:
        post_ids (list[str]): Identifiers for post.
        current_user_id (str): Identifier for current user.
    
    Returns:
        tuple[dict[str, int], dict[str, int], set[str]]: Likes count, comments count, and liked-by-
                                                         me flags by post id.
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


def create_post_like(post_id: str, user_id: str) -> bool:
    """Create one post like; return False when like already exists.
    
    Args:
        post_id (str): Post identifier.
        user_id (str): User identifier.
    
    Returns:
        bool: One post like; return False when like already exists.
    """
    try:
        require_supabase().table("post_likes").insert({"post_id": post_id, "user_id": user_id}).execute()
    except APIError as exc:
        if "duplicate" in str(exc).lower():
            return False
        raise HTTPException(status_code=502, detail=f"Like failed: {exc}") from exc
    return True


def delete_post_like(post_id: str, user_id: str) -> None:
    """Delete one post like for current user.
    
    Args:
        post_id (str): Post identifier.
        user_id (str): User identifier.
    
    Returns:
        None: None.
    """
    try:
        require_supabase().table("post_likes").delete().eq("post_id", post_id).eq("user_id", user_id).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Unlike failed: {exc}") from exc
