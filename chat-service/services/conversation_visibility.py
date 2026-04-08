"""Conversation visibility and participant state helpers."""

from datetime import datetime, timezone

from fastapi import HTTPException
from postgrest.exceptions import APIError

from core.context import logger, require_supabase
from stores.conversation_store import get_user_participation_row


def is_participation_hidden(participation_row: dict | None) -> bool:
    """Tell whether participant has hidden this conversation.
    
    Args:
        participation_row (dict | None): Parameter participation_row.
    
    Returns:
        bool: True if participation hidden, otherwise False.
    """
    if not participation_row:
        return False
    return participation_row.get("hidden_at") is not None


def ensure_user_visible_participant(conversation_id: str, user_id: str) -> dict:
    """Ensure user participates and conversation is not hidden for them.
    
    Args:
        conversation_id (str): Conversation identifier.
        user_id (str): User identifier.
    
    Returns:
        dict: User participates and conversation is not hidden for them.
    """
    participation_row = get_user_participation_row(conversation_id, user_id)
    if not participation_row:
        raise HTTPException(status_code=403, detail="Forbidden: user is not a participant of this conversation")
    if is_participation_hidden(participation_row):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return participation_row


def get_conversation_participants(conversation_id: str) -> list[str]:
    """List participant user ids for one conversation.
    
    Args:
        conversation_id (str): Conversation identifier.
    
    Returns:
        list[str]: Participant user ids for one conversation.
    """
    try:
        result = (
            require_supabase()
            .table("conversation_participants")
            .select("user_id")
            .eq("conversation_id", conversation_id)
            .execute()
        )
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Conversation participant lookup failed: {exc}") from exc

    return [str(row.get("user_id")) for row in (result.data or []) if row.get("user_id")]


def mask_conversation_for_user(conversation_id: str, user_id: str) -> None:
    """Hide conversation for one participant.
    
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
            .update({"hidden_at": now_iso})
            .eq("conversation_id", conversation_id)
            .eq("user_id", user_id)
            .execute()
        )
    except APIError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Conversation masking failed. Ensure conversation_participants.hidden_at "
                f"exists in DB schema: {exc}"
            ),
        ) from exc

    if not (updated.data or []):
        raise HTTPException(status_code=404, detail="Conversation participant not found")


def unhide_conversation_for_all_participants(conversation_id: str) -> None:
    """Best-effort unhide for all participants in a conversation.
    
    Args:
        conversation_id (str): Conversation identifier.
    
    Returns:
        None: None.
    """
    try:
        (
            require_supabase()
            .table("conversation_participants")
            .update({"hidden_at": None})
            .eq("conversation_id", conversation_id)
            .execute()
        )
    except APIError as exc:
        logger.warning("Conversation unhide skipped: %s", exc)
