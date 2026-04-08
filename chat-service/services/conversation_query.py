"""Conversation query and response assembly helpers."""

from fastapi import HTTPException
from postgrest.exceptions import APIError

from core.context import require_supabase
from services.conversation_visibility import get_conversation_participants
from stores.message_store import get_last_message_row, get_unread_count, serialize_message_rows
from schemas.models import ConversationResponse


def conversation_last_activity_iso(conversation_row: dict) -> str:
    """Return last activity timestamp based on latest message or creation time.
    
    Args:
        conversation_row (dict): Parameter conversation_row.
    
    Returns:
        str: Last activity timestamp based on latest message or creation time.
    """
    conversation_id = str(conversation_row.get("id"))
    last_message_row = get_last_message_row(conversation_id)
    if last_message_row and last_message_row.get("created_at"):
        return str(last_message_row.get("created_at"))
    return str(conversation_row.get("created_at") or "")


def find_existing_direct_conversation(current_user_id: str, target_user_id: str) -> dict | None:
    """Find existing 1-to-1 conversation between two users.
    
    Args:
        current_user_id (str): Identifier for current user.
        target_user_id (str): Identifier for target user.
    
    Returns:
        dict | None: Retrieved value.
    """
    try:
        current_participation = (
            require_supabase()
            .table("conversation_participants")
            .select("conversation_id")
            .eq("user_id", current_user_id)
            .execute()
        )
        target_participation = (
            require_supabase()
            .table("conversation_participants")
            .select("conversation_id")
            .eq("user_id", target_user_id)
            .execute()
        )
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Conversation lookup failed: {exc}") from exc

    current_ids = {
        str(row.get("conversation_id"))
        for row in (current_participation.data or [])
        if row.get("conversation_id")
    }
    target_ids = {
        str(row.get("conversation_id"))
        for row in (target_participation.data or [])
        if row.get("conversation_id")
    }
    common_ids = sorted(current_ids.intersection(target_ids))
    if not common_ids:
        return None

    try:
        conversations = require_supabase().table("conversations").select("*").in_("id", common_ids).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Conversation lookup failed: {exc}") from exc

    valid_rows: list[dict] = []
    for conversation_row in (conversations.data or []):
        conversation_id = str(conversation_row.get("id"))
        participant_set = {str(participant_id) for participant_id in get_conversation_participants(conversation_id)}
        if participant_set == {current_user_id, target_user_id}:
            valid_rows.append(conversation_row)

    if not valid_rows:
        return None

    valid_rows.sort(key=conversation_last_activity_iso, reverse=True)
    return valid_rows[0]


def deduplicate_direct_conversation_rows(conversation_rows: list[dict], current_user_id: str) -> list[dict]:
    """Deduplicate direct conversations by keeping the most recent one per target user.
    
    Args:
        conversation_rows (list[dict]): Parameter conversation_rows.
        current_user_id (str): Identifier for current user.
    
    Returns:
        list[dict]: Result of the operation.
    """
    if not conversation_rows:
        return []

    activity_cache: dict[str, str] = {}
    participants_cache: dict[str, list[str]] = {}

    def _activity_for(conversation_row: dict) -> str:
        """Return cached last-activity timestamp for a conversation row.
        
        Args:
            conversation_row (dict): Parameter conversation_row.
        
        Returns:
            str: Cached last-activity timestamp for a conversation row.
        """
        conversation_id = str(conversation_row.get("id"))
        if conversation_id not in activity_cache:
            activity_cache[conversation_id] = conversation_last_activity_iso(conversation_row)
        return activity_cache[conversation_id]

    def _participants_for(conversation_id: str) -> list[str]:
        """Return cached participant ids for a conversation.
        
        Args:
            conversation_id (str): Conversation identifier.
        
        Returns:
            list[str]: Cached participant ids for a conversation.
        """
        if conversation_id not in participants_cache:
            participants_cache[conversation_id] = get_conversation_participants(conversation_id)
        return participants_cache[conversation_id]

    deduped_map: dict[str, dict] = {}
    for conversation_row in conversation_rows:
        conversation_id = str(conversation_row.get("id"))
        participants = _participants_for(conversation_id)
        other_participants = [participant_id for participant_id in participants if participant_id != current_user_id]
        if len(other_participants) != 1:
            deduped_map[f"conversation:{conversation_id}"] = conversation_row
            _activity_for(conversation_row)
            continue

        direct_key = f"direct:{other_participants[0]}"
        existing_row = deduped_map.get(direct_key)
        if not existing_row:
            deduped_map[direct_key] = conversation_row
            _activity_for(conversation_row)
            continue

        if _activity_for(conversation_row) > _activity_for(existing_row):
            deduped_map[direct_key] = conversation_row

    deduped_rows = list(deduped_map.values())
    deduped_rows.sort(key=_activity_for, reverse=True)
    return deduped_rows


def build_conversation_response(
    conversation_row: dict,
    current_user_id: str,
    last_read_at: str | None,
) -> ConversationResponse:
    """Build conversation API response with last message and unread count.
    
    Args:
        conversation_row (dict): Parameter conversation_row.
        current_user_id (str): Identifier for current user.
        last_read_at (str | None): Parameter last_read_at.
    
    Returns:
        ConversationResponse: Conversation API response with last message and unread count.
    """
    conversation_id = str(conversation_row.get("id"))
    participant_ids = get_conversation_participants(conversation_id)
    last_message_row = get_last_message_row(conversation_id)
    last_message = serialize_message_rows([last_message_row])[0] if last_message_row else None
    unread_count = get_unread_count(conversation_id, current_user_id, last_read_at)

    return ConversationResponse(
        id=conversation_row.get("id"),
        created_at=conversation_row.get("created_at"),
        participant_ids=participant_ids,
        unread_count=unread_count,
        last_message=last_message,
    )
