"""Chat conversation and message proxy routes."""

from fastapi import APIRouter, Body, Depends, Query, Request

from routers.auth import CHAT_SERVICE_URL, proxy_request
from routers.security import require_bearer_token
from shared_schemas.models import ChatMessageCreateRequest, ConversationCreateRequest

chat_conversations_router = APIRouter()


@chat_conversations_router.post("/conversations", status_code=201, summary="Create conversation")
async def create_conversation(
    request: Request,
    payload: ConversationCreateRequest = Body(...),
    _: str = Depends(require_bearer_token),
):
    """Create a direct conversation by forwarding the request to Chat Service.
    
    Args:
        request (Request): Incoming FastAPI request context.
        payload (ConversationCreateRequest): Parsed request payload.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Direct conversation by forwarding the request to Chat Service.
    """
    return await proxy_request(
        method="POST",
        path="chat/conversations",
        json_body=payload.model_dump(mode="json", exclude_unset=True, exclude_none=True),
        headers=request.headers,
        params=request.query_params,
        base_url=CHAT_SERVICE_URL,
    )


@chat_conversations_router.get("/conversations", summary="List my conversations")
async def list_conversations(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: str = Depends(require_bearer_token),
):
    """Return the current user's paginated conversation list.
    
    Args:
        request (Request): Incoming FastAPI request context.
        limit (int): Maximum number of items to return.
        offset (int): Pagination offset.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Current user's paginated conversation list.
    """
    params = dict(request.query_params)
    params["limit"] = str(limit)
    params["offset"] = str(offset)
    return await proxy_request(
        method="GET",
        path="chat/conversations",
        headers=request.headers,
        params=params,
        base_url=CHAT_SERVICE_URL,
    )


@chat_conversations_router.get("/conversations/{conversation_id}/presence", summary="Get conversation participants presence")
async def get_conversation_presence(
    conversation_id: str,
    request: Request,
    _: str = Depends(require_bearer_token),
):
    """Get online participants for a conversation.
    
    Args:
        conversation_id (str): Conversation identifier.
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Online participants for a conversation.
    """
    return await proxy_request(
        method="GET",
        path=f"chat/conversations/{conversation_id}/presence",
        headers=request.headers,
        params=request.query_params,
        base_url=CHAT_SERVICE_URL,
    )


@chat_conversations_router.get("/conversations/{conversation_id}/messages", summary="List messages")
async def list_messages(
    conversation_id: str,
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    order: str = Query(default="asc"),
    _: str = Depends(require_bearer_token),
):
    """List paginated messages for one conversation.
    
    Args:
        conversation_id (str): Conversation identifier.
        request (Request): Incoming FastAPI request context.
        limit (int): Maximum number of items to return.
        offset (int): Pagination offset.
        order (str): Parameter order.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Paginated messages for one conversation.
    """
    params = dict(request.query_params)
    params["limit"] = str(limit)
    params["offset"] = str(offset)
    params["order"] = order
    return await proxy_request(
        method="GET",
        path=f"chat/conversations/{conversation_id}/messages",
        headers=request.headers,
        params=params,
        base_url=CHAT_SERVICE_URL,
    )


@chat_conversations_router.post("/conversations/{conversation_id}/messages", status_code=201, summary="Send message (HTTP)")
async def send_message(
    conversation_id: str,
    request: Request,
    payload: ChatMessageCreateRequest = Body(...),
    _: str = Depends(require_bearer_token),
):
    """Send a message in a conversation through HTTP.
    
    Args:
        conversation_id (str): Conversation identifier.
        request (Request): Incoming FastAPI request context.
        payload (ChatMessageCreateRequest): Parsed request payload.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Result of the operation.
    """
    return await proxy_request(
        method="POST",
        path=f"chat/conversations/{conversation_id}/messages",
        json_body=payload.model_dump(mode="json", exclude_unset=True, exclude_none=True),
        headers=request.headers,
        params=request.query_params,
        base_url=CHAT_SERVICE_URL,
    )
