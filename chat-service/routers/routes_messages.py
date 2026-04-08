"""Message routes for chat conversations."""

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Path, Query
from postgrest.exceptions import APIError

from core.auth_utils import resolve_user_id
from utils.content_utils import normalize_content
from core.context import require_supabase
from stores.conversation_store import ensure_conversation_exists, ensure_user_participant
from services.conversation_visibility import ensure_user_visible_participant
from services.message_flow import create_and_broadcast_message
from stores.message_store import serialize_message_rows
from schemas.models import MessageCreateRequest, MessageResponse

chat_messages_router = APIRouter()


@chat_messages_router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse],
    summary="List messages of a conversation",
)
def list_conversation_messages(
    conversation_id: UUID = Path(...),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    order: str = Query(default="asc"),
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """List messages for one conversation with pagination and order.
    
    Args:
        conversation_id (UUID): Conversation identifier.
        limit (int): Maximum number of items to return.
        offset (int): Pagination offset.
        order (str): Parameter order.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Messages for one conversation with pagination and order.
    """
    current_user_id = resolve_user_id(x_user_id, x_access_token)
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: missing or invalid access token")

    conversation_id_str = str(conversation_id)
    ensure_conversation_exists(conversation_id_str)
    ensure_user_visible_participant(conversation_id_str, current_user_id)

    normalized_order = order.lower().strip()
    if normalized_order not in {"asc", "desc"}:
        raise HTTPException(status_code=422, detail="Invalid order. Use 'asc' or 'desc'")

    try:
        result = (
            require_supabase()
            .table("messages")
            .select("*")
            .eq("conversation_id", conversation_id_str)
            .order("created_at", desc=(normalized_order == "desc"))
            .range(offset, offset + limit - 1)
            .execute()
        )
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Message list failed: {exc}") from exc

    return serialize_message_rows(result.data or [])


@chat_messages_router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=201,
    summary="Create message (HTTP)",
)
async def create_message(
    conversation_id: UUID,
    payload: MessageCreateRequest,
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Create one message in a conversation and broadcast in realtime.
    
    Args:
        conversation_id (UUID): Conversation identifier.
        payload (MessageCreateRequest): Parsed request payload.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: One message in a conversation and broadcast in realtime.
    """
    current_user_id = resolve_user_id(x_user_id, x_access_token)
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: missing or invalid access token")

    conversation_id_str = str(conversation_id)
    ensure_conversation_exists(conversation_id_str)
    ensure_user_participant(conversation_id_str, current_user_id)

    content = normalize_content(payload.content)
    if not content:
        raise HTTPException(status_code=422, detail="Message content cannot be empty")

    return await create_and_broadcast_message(conversation_id_str, current_user_id, content)
