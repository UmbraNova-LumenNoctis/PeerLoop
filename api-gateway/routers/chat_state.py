"""Chat state mutation proxy routes."""

from fastapi import APIRouter, Depends, Request

from routers.auth import CHAT_SERVICE_URL, proxy_request
from routers.security import require_bearer_token

chat_state_router = APIRouter()


@chat_state_router.patch("/conversations/{conversation_id}/read", summary="Mark conversation as read")
async def mark_conversation_read(
    conversation_id: str,
    request: Request,
    _: str = Depends(require_bearer_token),
):
    """Mark a conversation as read for the current user.
    
    Args:
        conversation_id (str): Conversation identifier.
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Result of the operation.
    """
    return await proxy_request(
        method="PATCH",
        path=f"chat/conversations/{conversation_id}/read",
        headers=request.headers,
        params=request.query_params,
        base_url=CHAT_SERVICE_URL,
    )


@chat_state_router.delete("/conversations/{conversation_id}", summary="Hide conversation for current user")
async def delete_conversation(
    conversation_id: str,
    request: Request,
    _: str = Depends(require_bearer_token),
):
    """Hide a conversation for the current user.
    
    Args:
        conversation_id (str): Conversation identifier.
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Result of the operation.
    """
    return await proxy_request(
        method="DELETE",
        path=f"chat/conversations/{conversation_id}",
        headers=request.headers,
        params=request.query_params,
        base_url=CHAT_SERVICE_URL,
    )
