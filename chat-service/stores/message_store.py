"""Message persistence and serialization helpers."""

from datetime import datetime, timezone

from fastapi import HTTPException
from postgrest.exceptions import APIError

from core.context import require_supabase
from schemas.models import MessageResponse
from stores.user_store import get_avatar_url_map, get_users_map


def serialize_message_rows(message_rows: list[dict]) -> list[MessageResponse]:
    """Serialize raw DB message rows into API response models.
    
    Args:
        message_rows (list[dict]): Parameter message_rows.
    
    Returns:
        list[MessageResponse]: Raw DB message rows into API response models.
    """
    if not message_rows:
        return []

    sender_ids = [str(row.get("sender_id")) for row in message_rows if row.get("sender_id")]
    users_map = get_users_map(sender_ids)
    avatar_ids = [str(user.get("avatar_id")) for user in users_map.values() if user.get("avatar_id")]
    avatar_urls = get_avatar_url_map(avatar_ids)

    serialized = []
    for row in message_rows:
        sender_id = str(row.get("sender_id"))
        sender = users_map.get(sender_id, {})
        avatar_id = sender.get("avatar_id")
        serialized.append(
            MessageResponse(
                id=row.get("id"),
                conversation_id=row.get("conversation_id"),
                sender_id=row.get("sender_id"),
                content=row.get("content") or "",
                created_at=row.get("created_at"),
                sender_pseudo=sender.get("pseudo"),
                sender_avatar_id=avatar_id,
                sender_avatar_url=avatar_urls.get(str(avatar_id)) if avatar_id else None,
            )
        )
    return serialized


def get_last_message_row(conversation_id: str) -> dict | None:
    """Fetch most recent message row for one conversation.
    
    Args:
        conversation_id (str): Conversation identifier.
    
    Returns:
        dict | None: Most recent message row for one conversation.
    """
    try:
        result = (
            require_supabase()
            .table("messages")
            .select("*")
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Message lookup failed: {exc}") from exc

    rows = result.data or []
    return rows[0] if rows else None


def create_message_row(conversation_id: str, sender_id: str, content: str) -> dict:
    """Insert a new message row.
    
    Args:
        conversation_id (str): Conversation identifier.
        sender_id (str): Identifier for sender.
        content (str): Text content.
    
    Returns:
        dict: Constructed value.
    """
    try:
        created = (
            require_supabase()
            .table("messages")
            .insert({"conversation_id": conversation_id, "sender_id": sender_id, "content": content})
            .execute()
        )
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Message creation failed: {exc}") from exc

    rows = created.data or []
    if not rows:
        raise HTTPException(status_code=502, detail="Message was created but not returned")
    return rows[0]


def get_unread_count(conversation_id: str, current_user_id: str, last_read_at: str | None) -> int:
    """Count unread messages for user in one conversation.
    
    Args:
        conversation_id (str): Conversation identifier.
        current_user_id (str): Identifier for current user.
        last_read_at (str | None): Parameter last_read_at.
    
    Returns:
        int: Retrieved value.
    """
    try:
        query = (
            require_supabase()
            .table("messages")
            .select("id")
            .eq("conversation_id", conversation_id)
            .neq("sender_id", current_user_id)
        )
        if last_read_at:
            query = query.gt("created_at", last_read_at)
        result = query.execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Unread count lookup failed: {exc}") from exc

    return len(result.data or [])


def mark_conversation_read(conversation_id: str, user_id: str) -> None:
    """Set participant last_read_at to now for one conversation.
    
    Args:
        conversation_id (str): Conversation identifier.
        user_id (str): User identifier.
    
    Returns:
        None: None.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        updated = (
            require_supabase()
            .table("conversation_participants")
            .update({"last_read_at": now_iso})
            .eq("conversation_id", conversation_id)
            .eq("user_id", user_id)
            .execute()
        )
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Conversation read update failed: {exc}") from exc

    if not (updated.data or []):
        raise HTTPException(status_code=404, detail="Conversation participant not found")
