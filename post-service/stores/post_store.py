"""Post storage helpers."""

from fastapi import HTTPException
from postgrest.exceptions import APIError

from core.context import require_supabase


def get_post_by_id(post_id: str) -> dict | None:
    """Fetch one post row by id.
    
    Args:
        post_id (str): Post identifier.
    
    Returns:
        dict | None: One post row by id.
    """
    try:
        result = require_supabase().table("posts").select("*").eq("id", post_id).limit(1).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Post lookup failed: {exc}") from exc

    rows = result.data or []
    return rows[0] if rows else None


def create_post_row(user_id: str, content: str | None, media_id: str | None) -> dict:
    """Create one post row and return inserted row.
    
    Args:
        user_id (str): User identifier.
        content (str | None): Text content.
        media_id (str | None): Media identifier.
    
    Returns:
        dict: One post row and return inserted row.
    """
    try:
        created = require_supabase().table("posts").insert({"user_id": user_id, "content": content, "media_id": media_id}).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Post creation failed: {exc}") from exc

    rows = created.data or []
    if not rows:
        raise HTTPException(status_code=502, detail="Post was created but not returned")
    return rows[0]


def update_post_row(post_id: str, updates: dict[str, object]) -> dict:
    """Update post row and return updated snapshot.
    
    Args:
        post_id (str): Post identifier.
        updates (dict[str, object]): Parameter updates.
    
    Returns:
        dict: Result of the operation.
    """
    try:
        updated = require_supabase().table("posts").update(updates).eq("id", post_id).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Post update failed: {exc}") from exc

    rows = updated.data or []
    if rows:
        return rows[0]

    row = get_post_by_id(post_id)
    if not row:
        raise HTTPException(status_code=404, detail="Post not found")
    return row


def delete_post_with_relations(post_id: str) -> None:
    """Delete post and dependent likes/comments rows.
    
    Args:
        post_id (str): Post identifier.
    
    Returns:
        None: None.
    """
    try:
        require_supabase().table("post_likes").delete().eq("post_id", post_id).execute()
        require_supabase().table("comments").delete().eq("post_id", post_id).execute()
        require_supabase().table("posts").delete().eq("id", post_id).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Post delete failed: {exc}") from exc
