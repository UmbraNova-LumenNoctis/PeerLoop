"""Friendship storage helpers."""

from fastapi import HTTPException
from postgrest.exceptions import APIError

from core.context import require_supabase


def get_friendship_between(user_1_id: str, user_2_id: str) -> dict | None:
    """Return existing friendship row between two users in either direction.
    
    Args:
        user_1_id (str): Identifier for user 1.
        user_2_id (str): Identifier for user 2.
    
    Returns:
        dict | None: Existing friendship row between two users in either direction.
    """
    try:
        first = (
            require_supabase()
            .table("friendships")
            .select("*")
            .eq("user_a_id", user_1_id)
            .eq("user_b_id", user_2_id)
            .limit(1)
            .execute()
        )
        if first.data:
            return first.data[0]

        second = (
            require_supabase()
            .table("friendships")
            .select("*")
            .eq("user_a_id", user_2_id)
            .eq("user_b_id", user_1_id)
            .limit(1)
            .execute()
        )
        return second.data[0] if second.data else None
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Friendship lookup failed: {exc}") from exc


def get_friendship_by_id(friendship_id: str) -> dict | None:
    """Return one friendship row by id.
    
    Args:
        friendship_id (str): Identifier for friendship.
    
    Returns:
        dict | None: One friendship row by id.
    """
    try:
        result = require_supabase().table("friendships").select("*").eq("id", friendship_id).limit(1).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Friendship lookup failed: {exc}") from exc

    rows = result.data or []
    return rows[0] if rows else None


def ensure_participant(friendship_row: dict, user_id: str) -> None:
    """Validate user participates in provided friendship row.
    
    Args:
        friendship_row (dict): Parameter friendship_row.
        user_id (str): User identifier.
    
    Returns:
        None: None.
    """
    participants = {str(friendship_row.get("user_a_id")), str(friendship_row.get("user_b_id"))}
    if user_id not in participants:
        raise HTTPException(status_code=403, detail="Forbidden: not a participant of this friendship")


def list_friendship_rows(current_user_id: str, status: str | None, direction: str | None) -> list[dict]:
    """List friendship rows for one user with optional status/direction filters.
    
    Args:
        current_user_id (str): Identifier for current user.
        status (str | None): Parameter status.
        direction (str | None): Parameter direction.
    
    Returns:
        list[dict]: Friendship rows for one user with optional status/direction filters.
    """
    try:
        result_as_a = require_supabase().table("friendships").select("*").eq("user_a_id", current_user_id).execute()
        result_as_b = require_supabase().table("friendships").select("*").eq("user_b_id", current_user_id).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Friendship list failed: {exc}") from exc

    rows = [*(result_as_a.data or []), *(result_as_b.data or [])]

    if status is not None:
        rows = [row for row in rows if (row.get("status") or "").lower() == status]
    if direction == "incoming":
        rows = [row for row in rows if str(row.get("user_b_id")) == current_user_id]
    elif direction == "outgoing":
        rows = [row for row in rows if str(row.get("user_a_id")) == current_user_id]

    deduped_rows: list[dict] = []
    seen_ids: set[str] = set()
    for row in rows:
        row_id = str(row.get("id"))
        if row_id in seen_ids:
            continue
        seen_ids.add(row_id)
        deduped_rows.append(row)

    deduped_rows.sort(key=lambda row: row.get("created_at") or "", reverse=True)
    return deduped_rows


def update_friendship_status(friendship_id: str, status: str) -> dict:
    """Update friendship status and return resulting row.
    
    Uses DELETE + INSERT instead of UPDATE to avoid a stale
    ``update_timestamp`` trigger that references a removed
    ``updated_at`` column on the ``friendships`` table.
    
    Args:
        friendship_id (str): Identifier for friendship.
        status (str): Parameter status.
    
    Returns:
        dict: Result of the operation.
    """
    row = get_friendship_by_id(friendship_id)
    if not row:
        raise HTTPException(status_code=404, detail="Friendship not found")

    sb = require_supabase()

    try:
        sb.table("friendships").delete().eq("id", friendship_id).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Friendship delete (for re-insert) failed: {exc}") from exc

    new_row = {
        "id": row["id"],
        "user_a_id": row["user_a_id"],
        "user_b_id": row["user_b_id"],
        "status": status,
        "created_at": row["created_at"],
    }

    try:
        inserted = sb.table("friendships").insert(new_row).execute()
    except APIError as exc:
        # Rollback: try to restore the original row
        try:
            sb.table("friendships").insert({
                "id": row["id"],
                "user_a_id": row["user_a_id"],
                "user_b_id": row["user_b_id"],
                "status": row["status"],
                "created_at": row["created_at"],
            }).execute()
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=f"Friendship re-insert failed: {exc}") from exc

    rows = inserted.data or []
    if rows:
        return rows[0]

    fallback_row = get_friendship_by_id(friendship_id)
    if not fallback_row:
        raise HTTPException(status_code=404, detail="Friendship not found after update")
    return fallback_row
