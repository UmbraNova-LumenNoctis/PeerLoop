"""Comment storage helpers."""

from fastapi import HTTPException
from postgrest.exceptions import APIError

from core.context import require_supabase


def get_comment_by_id(comment_id: str) -> dict | None:
    """Fetch one comment row by id.
    
    Args:
        comment_id (str): Comment identifier.
    
    Returns:
        dict | None: One comment row by id.
    """
    try:
        result = require_supabase().table("comments").select("*").eq("id", comment_id).limit(1).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Comment lookup failed: {exc}") from exc

    rows = result.data or []
    return rows[0] if rows else None


def list_comment_rows_for_post(post_id: str) -> list[dict]:
    """List comments for post ordered by creation timestamp.
    
    Args:
        post_id (str): Post identifier.
    
    Returns:
        list[dict]: Comments for post ordered by creation timestamp.
    """
    try:
        result = require_supabase().table("comments").select("*").eq("post_id", post_id).order("created_at", desc=False).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Comment list failed: {exc}") from exc
    return result.data or []


def create_comment_row(post_id: str, user_id: str, content: str, parent_comment_id: str | None) -> dict:
    """Create one comment row and return inserted row.
    
    Args:
        post_id (str): Post identifier.
        user_id (str): User identifier.
        content (str): Text content.
        parent_comment_id (str | None): Identifier for parent comment.
    
    Returns:
        dict: One comment row and return inserted row.
    """
    payload: dict[str, str] = {"post_id": post_id, "user_id": user_id, "content": content}
    if parent_comment_id:
        payload["parent_comment_id"] = parent_comment_id

    try:
        created = require_supabase().table("comments").insert(payload).execute()
    except APIError as exc:
        if parent_comment_id and "parent_comment_id" in str(exc).lower():
            raise HTTPException(
                status_code=500,
                detail="Reply support is not fully migrated. Add comments.parent_comment_id in database schema.",
            )
        raise HTTPException(status_code=502, detail=f"Comment creation failed: {exc}") from exc

    rows = created.data or []
    if not rows:
        raise HTTPException(status_code=502, detail="Comment was created but not returned")
    return rows[0]


def update_comment_content(comment_id: str, content: str) -> dict:
    """Update comment content and return updated row.
    
    Args:
        comment_id (str): Comment identifier.
        content (str): Text content.
    
    Returns:
        dict: Result of the operation.
    """
    try:
        updated = require_supabase().table("comments").update({"content": content}).eq("id", comment_id).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Comment update failed: {exc}") from exc

    rows = updated.data or []
    if rows:
        return rows[0]

    row = get_comment_by_id(comment_id)
    if not row:
        raise HTTPException(status_code=404, detail="Comment not found")
    return row


def delete_comments_by_ids(comment_ids: list[str]) -> None:
    """Delete one comment or a full thread by id list.
    
    Args:
        comment_ids (list[str]): Identifiers for comment.
    
    Returns:
        None: None.
    """
    if not comment_ids:
        return

    try:
        if len(comment_ids) == 1:
            require_supabase().table("comments").delete().eq("id", comment_ids[0]).execute()
        else:
            require_supabase().table("comments").delete().in_("id", comment_ids).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Comment delete failed: {exc}") from exc
