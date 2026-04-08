"""Comment tree traversal helpers."""

from fastapi import HTTPException
from postgrest.exceptions import APIError

from core.context import require_supabase


def collect_comment_thread_ids(root_comment_id: str) -> list[str]:
    """Collect all descendant comment ids for a root comment.
    
    Args:
        root_comment_id (str): Identifier for root comment.
    
    Returns:
        list[str]: Result of the operation.
    """
    collected: set[str] = set()
    frontier: list[str] = [root_comment_id]

    while frontier:
        try:
            result = require_supabase().table("comments").select("id").in_("parent_comment_id", frontier).execute()
        except APIError as exc:
            if "parent_comment_id" in str(exc).lower():
                return [root_comment_id]
            raise HTTPException(status_code=502, detail=f"Comment thread lookup failed: {exc}") from exc

        next_frontier: list[str] = []
        for row in result.data or []:
            child_id = row.get("id")
            if not child_id:
                continue
            child_key = str(child_id)
            if child_key in collected or child_key == root_comment_id:
                continue
            collected.add(child_key)
            next_frontier.append(child_key)

        frontier = next_frontier

    return [root_comment_id, *collected]
