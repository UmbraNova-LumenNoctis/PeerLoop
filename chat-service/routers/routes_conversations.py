"""Conversation routes for chat service."""

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query
from postgrest.exceptions import APIError

from core.auth_utils import resolve_user_id
from services.connection_manager import connection_manager
from core.context import require_supabase
from services.conversation_query import (
    build_conversation_response,
    deduplicate_direct_conversation_rows,
    find_existing_direct_conversation,
)
from stores.conversation_store import (
    ensure_conversation_exists,
    ensure_user_participant,
    get_user_participation_row,
)
from services.conversation_visibility import (
    ensure_user_visible_participant,
    is_participation_hidden,
    mask_conversation_for_user,
    unhide_conversation_for_all_participants,
)
from stores.message_store import mark_conversation_read
from schemas.models import ConversationCreateRequest, ConversationResponse
from services.notifications import send_notification
from stores.user_store import ensure_users_exist

chat_conversations_router = APIRouter()


@chat_conversations_router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=201,
    summary="Create conversation",
)
def create_conversation(
    payload: ConversationCreateRequest,
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Create (or reuse) a direct conversation between two users.
    
    Args:
        payload (ConversationCreateRequest): Parsed request payload.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: (or reuse) a direct conversation between two users.
    """
    current_user_id = resolve_user_id(x_user_id, x_access_token)
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: missing or invalid access token")

    target_participants = {str(participant_id) for participant_id in payload.participant_ids}
    target_participants.discard(current_user_id)
    if not target_participants:
        raise HTTPException(status_code=422, detail="participant_ids must include at least one other user")
    if len(target_participants) != 1:
        raise HTTPException(status_code=422, detail="Direct conversation requires exactly one target participant")

    participant_ids = sorted(target_participants | {current_user_id})
    ensure_users_exist(participant_ids)

    target_user_id = next(iter(target_participants))
    existing_direct_conversation = find_existing_direct_conversation(current_user_id, target_user_id)
    if existing_direct_conversation:
        existing_conversation_id = str(existing_direct_conversation.get("id"))
        unhide_conversation_for_all_participants(existing_conversation_id)
        current_participation = get_user_participation_row(existing_conversation_id, current_user_id)
        last_read_at = current_participation.get("last_read_at") if current_participation else None
        return build_conversation_response(existing_direct_conversation, current_user_id, last_read_at)

    try:
        created_conversation = require_supabase().table("conversations").insert({}).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Conversation creation failed: {exc}") from exc

    conversation_rows = created_conversation.data or []
    if not conversation_rows:
        raise HTTPException(status_code=502, detail="Conversation was created but not returned")
    conversation_row = conversation_rows[0]
    conversation_id = str(conversation_row.get("id"))

    participant_rows = [{"conversation_id": conversation_id, "user_id": participant_id} for participant_id in participant_ids]
    try:
        require_supabase().table("conversation_participants").insert(participant_rows).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Conversation participants creation failed: {exc}") from exc

    try:
        my_participation = (
            require_supabase()
            .table("conversation_participants")
            .select("last_read_at")
            .eq("conversation_id", conversation_id)
            .eq("user_id", current_user_id)
            .limit(1)
            .execute()
        )
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Conversation participant lookup failed: {exc}") from exc

    participation_rows = my_participation.data or []
    last_read_at = participation_rows[0].get("last_read_at") if participation_rows else None

    for participant_id in participant_ids:
        send_notification(
            target_user_id=participant_id,
            notification_type="chat_conversation_created",
            content=(
                "Conversation created"
                if participant_id == current_user_id
                else "You were added to a conversation"
            ),
            source_id=conversation_id,
        )

    return build_conversation_response(conversation_row, current_user_id, last_read_at)


@chat_conversations_router.get(
    "/conversations",
    response_model=list[ConversationResponse],
    summary="List my conversations",
)
def list_conversations(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """List current user's visible conversations with pagination.
    
    Args:
        limit (int): Maximum number of items to return.
        offset (int): Pagination offset.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Current user's visible conversations with pagination.
    """
    current_user_id = resolve_user_id(x_user_id, x_access_token)
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: missing or invalid access token")

    try:
        participation = (
            require_supabase()
            .table("conversation_participants")
            .select("*")
            .eq("user_id", current_user_id)
            .execute()
        )
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Conversation list failed: {exc}") from exc

    participation_rows = participation.data or []
    visible_participation_rows = [row for row in participation_rows if not is_participation_hidden(row)]
    if not visible_participation_rows:
        return []

    last_read_map = {
        str(row.get("conversation_id")): row.get("last_read_at")
        for row in visible_participation_rows
        if row.get("conversation_id")
    }
    conversation_ids = list(last_read_map.keys())

    try:
        conversations_result = require_supabase().table("conversations").select("*").in_("id", conversation_ids).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Conversation list failed: {exc}") from exc

    conversation_rows = conversations_result.data or []
    deduped_rows = deduplicate_direct_conversation_rows(conversation_rows, current_user_id)
    paged_rows = deduped_rows[offset : offset + limit]

    return [
        build_conversation_response(
            conversation_row=row,
            current_user_id=current_user_id,
            last_read_at=last_read_map.get(str(row.get("id"))),
        )
        for row in paged_rows
    ]


@chat_conversations_router.patch("/conversations/{conversation_id}/read", summary="Mark conversation as read")
def mark_one_conversation_read(
    conversation_id: UUID,
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Mark conversation as read for current user.
    
    Args:
        conversation_id (UUID): Conversation identifier.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Result of the operation.
    """
    current_user_id = resolve_user_id(x_user_id, x_access_token)
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: missing or invalid access token")

    conversation_id_str = str(conversation_id)
    ensure_conversation_exists(conversation_id_str)
    ensure_user_visible_participant(conversation_id_str, current_user_id)
    mark_conversation_read(conversation_id_str, current_user_id)
    return {"message": "Conversation marked as read", "conversation_id": conversation_id_str}


@chat_conversations_router.delete("/conversations/{conversation_id}", summary="Hide conversation for current user")
async def delete_conversation(
    conversation_id: UUID,
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Hide conversation for current user and close active sockets for this conversation.
    
    Args:
        conversation_id (UUID): Conversation identifier.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Result of the operation.
    """
    current_user_id = resolve_user_id(x_user_id, x_access_token)
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: missing or invalid access token")

    conversation_id_str = str(conversation_id)
    ensure_conversation_exists(conversation_id_str)
    ensure_user_participant(conversation_id_str, current_user_id)
    mask_conversation_for_user(conversation_id_str, current_user_id)

    detached_sockets = connection_manager.detach_user_from_conversation(conversation_id_str, current_user_id)
    for websocket in detached_sockets:
        try:
            await websocket.close(code=4403)
        except Exception:
            pass

    if detached_sockets:
        await connection_manager.broadcast(
            conversation_id_str,
            {
                "type": "presence",
                "event": "leave",
                "conversation_id": conversation_id_str,
                "user_id": current_user_id,
            },
        )

    return {
        "message": "Conversation hidden for current user",
        "conversation_id": conversation_id_str,
        "hidden_for_user": True,
        "deleted_for_all": False,
    }
