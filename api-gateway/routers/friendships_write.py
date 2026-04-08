"""Write/update friendship proxy routes."""

from fastapi import APIRouter, Body, Depends, Request

from routers.auth import FRIENDSHIP_SERVICE_URL, proxy_request
from routers.security import require_bearer_token
from shared_schemas.models import FriendshipCreateRequest

friendships_write_router = APIRouter()


@friendships_write_router.post("/request", status_code=201, summary="Send friendship request")
async def send_request(
    request: Request,
    payload: FriendshipCreateRequest = Body(...),
    _: str = Depends(require_bearer_token),
):
    """Create a new friendship request.
    
    Args:
        request (Request): Incoming FastAPI request context.
        payload (FriendshipCreateRequest): Parsed request payload.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: New friendship request.
    """
    return await proxy_request(
        method="POST",
        path="friendships/request",
        json_body=payload.model_dump(mode="json", exclude_unset=True, exclude_none=True),
        headers=request.headers,
        params=request.query_params,
        base_url=FRIENDSHIP_SERVICE_URL,
    )


@friendships_write_router.patch("/{friendship_id}/accept", summary="Accept friendship request")
async def accept_friendship(
    friendship_id: str,
    request: Request,
    _: str = Depends(require_bearer_token),
):
    """Accept an existing friendship request.
    
    Args:
        friendship_id (str): Identifier for friendship.
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Result of the operation.
    """
    return await proxy_request(
        method="PATCH",
        path=f"friendships/{friendship_id}/accept",
        headers=request.headers,
        params=request.query_params,
        base_url=FRIENDSHIP_SERVICE_URL,
    )


@friendships_write_router.patch("/{friendship_id}/block", summary="Block friendship")
async def block_friendship(
    friendship_id: str,
    request: Request,
    _: str = Depends(require_bearer_token),
):
    """Block an existing friendship.
    
    Args:
        friendship_id (str): Identifier for friendship.
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Result of the operation.
    """
    return await proxy_request(
        method="PATCH",
        path=f"friendships/{friendship_id}/block",
        headers=request.headers,
        params=request.query_params,
        base_url=FRIENDSHIP_SERVICE_URL,
    )


@friendships_write_router.delete("/{friendship_id}", summary="Delete friendship")
async def delete_friendship(
    friendship_id: str,
    request: Request,
    _: str = Depends(require_bearer_token),
):
    """Delete an existing friendship.
    
    Args:
        friendship_id (str): Identifier for friendship.
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Result of the operation.
    """
    return await proxy_request(
        method="DELETE",
        path=f"friendships/{friendship_id}",
        headers=request.headers,
        params=request.query_params,
        base_url=FRIENDSHIP_SERVICE_URL,
    )
