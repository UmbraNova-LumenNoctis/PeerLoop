"""Conversation and participant storage helpers."""

from fastapi import HTTPException
from postgrest.exceptions import APIError

from core.context import require_supabase


def get_conversation_row(conversation_id: str) -> dict | None:
    """Fetch one conversation row by id.
    
    Args:
        conversation_id (str): Conversation identifier.
    
    Returns:
        dict | None: One conversation row by id.
    """
    try:
        result = require_supabase().table("conversations").select("*").eq("id", conversation_id).limit(1).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Conversation lookup failed: {exc}") from exc

    rows = result.data or []
    return rows[0] if rows else None


def ensure_conversation_exists(conversation_id: str) -> dict:
    """Ensure conversation exists and return its row.
    
    Args:
        conversation_id (str): Conversation identifier.
    
    Returns:
        dict: Conversation exists and return its row.
    """
    conversation_row = get_conversation_row(conversation_id)
    if not conversation_row:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation_row


def is_user_participant(conversation_id: str, user_id: str) -> bool:
    """Tell whether user participates in a conversation.
    
    Args:
        conversation_id (str): Conversation identifier.
        user_id (str): User identifier.
    
    Returns:
        bool: True if user participant, otherwise False.
    """
    try:
        result = (
            require_supabase()
            .table("conversation_participants")
            .select("conversation_id")
            .eq("conversation_id", conversation_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Conversation participant lookup failed: {exc}") from exc

    return bool(result.data or [])


def ensure_user_participant(conversation_id: str, user_id: str) -> None:
    """Raise when user is not participant of a conversation.
    
    Args:
        conversation_id (str): Conversation identifier.
        user_id (str): User identifier.
    
    Returns:
        None: None.
    """
    if not is_user_participant(conversation_id, user_id):
        raise HTTPException(status_code=403, detail="Forbidden: user is not a participant of this conversation")


def get_user_participation_row(conversation_id: str, user_id: str) -> dict | None:
    """Fetch one conversation participant row for user.
    
    Args:
        conversation_id (str): Conversation identifier.
        user_id (str): User identifier.
    
    Returns:
        dict | None: One conversation participant row for user.
    """
    try:
        result = (
            require_supabase()
            .table("conversation_participants")
            .select("*")
            .eq("conversation_id", conversation_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Conversation participant lookup failed: {exc}") from exc

    rows = result.data or []
    return rows[0] if rows else None
