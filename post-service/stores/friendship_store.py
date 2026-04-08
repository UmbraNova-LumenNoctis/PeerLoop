"""Friendship projection helpers for post feed."""

from fastapi import HTTPException
from postgrest.exceptions import APIError

from core.context import require_supabase


def get_accepted_friend_user_ids(current_user_id: str) -> set[str]:
    """Return accepted friend user ids for current user.
    
    Args:
        current_user_id (str): Identifier for current user.
    
    Returns:
        set[str]: Accepted friend user ids for current user.
    """
    try:
        rows_as_sender = (
            require_supabase()
            .table("friendships")
            .select("user_b_id")
            .eq("user_a_id", current_user_id)
            .eq("status", "accepted")
            .execute()
        )
        rows_as_receiver = (
            require_supabase()
            .table("friendships")
            .select("user_a_id")
            .eq("user_b_id", current_user_id)
            .eq("status", "accepted")
            .execute()
        )
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Friendship lookup failed: {exc}") from exc

    friend_ids: set[str] = set()
    for row in rows_as_sender.data or []:
        user_id = row.get("user_b_id")
        if user_id:
            friend_ids.add(str(user_id))

    for row in rows_as_receiver.data or []:
        user_id = row.get("user_a_id")
        if user_id:
            friend_ids.add(str(user_id))

    return friend_ids
