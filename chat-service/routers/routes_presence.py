"""Presence routes for chat service."""

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Path, Query

from core.auth_utils import is_internal_token_valid, resolve_user_id
from services.connection_manager import connection_manager
from stores.conversation_store import ensure_conversation_exists
from services.conversation_visibility import ensure_user_visible_participant, get_conversation_participants

presence_internal_router = APIRouter(tags=["Presence"])
chat_presence_router = APIRouter()


@presence_internal_router.get("/presence/internal", tags=["Presence"])
def get_presence_internal(
    user_ids: str | None = Query(default=None, description="Comma-separated user ids"),
    x_internal_service_token: str = Header(None),
):
    """Return online user ids for trusted internal callers.
    
    Args:
        user_ids (str | None): Identifiers for user.
        x_internal_service_token (str): Parameter x_internal_service_token.
    
    Returns:
        Any: Online user ids for trusted internal callers.
    """
    if not is_internal_token_valid(x_internal_service_token):
        raise HTTPException(status_code=401, detail="Unauthorized internal request")

    requested_user_ids = None
    if user_ids is not None:
        requested_user_ids = [user_id.strip() for user_id in user_ids.split(",") if user_id.strip()]
    online_user_ids = sorted(connection_manager.get_online_user_ids(requested_user_ids))
    return {"online_user_ids": online_user_ids}


@chat_presence_router.get(
    "/conversations/{conversation_id}/presence",
    summary="Get online participants for a conversation",
)
def get_conversation_presence(
    conversation_id: UUID = Path(...),
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Return online participant ids for one visible conversation.
    
    Args:
        conversation_id (UUID): Conversation identifier.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Online participant ids for one visible conversation.
    """
    current_user_id = resolve_user_id(x_user_id, x_access_token)
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: missing or invalid access token")

    conversation_id_str = str(conversation_id)
    ensure_conversation_exists(conversation_id_str)
    ensure_user_visible_participant(conversation_id_str, current_user_id)

    participant_ids = get_conversation_participants(conversation_id_str)
    online_user_ids = sorted(connection_manager.get_online_user_ids(participant_ids))
    return {"conversation_id": conversation_id_str, "online_user_ids": online_user_ids}
