"""Read-only friendship proxy routes."""

from typing import Literal

from fastapi import APIRouter, Depends, Query, Request

from routers.auth import FRIENDSHIP_SERVICE_URL, proxy_request
from routers.security import require_bearer_token

friendships_read_router = APIRouter()


@friendships_read_router.get("", summary="List friendships")
async def list_friendships(
    request: Request,
    status: Literal["pending", "accepted", "blocked"] | None = Query(default=None),
    direction: Literal["incoming", "outgoing"] | None = Query(default=None),
    _: str = Depends(require_bearer_token),
):
    """List friendships with optional status and direction filters.
    
    Args:
        request (Request): Incoming FastAPI request context.
        status (Literal['pending', 'accepted', 'blocked'] | None): Parameter status.
        direction (Literal['incoming', 'outgoing'] | None): Parameter direction.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Friendships with optional status and direction filters.
    """
    params = dict(request.query_params)
    if status is not None:
        params["status"] = status
    if direction is not None:
        params["direction"] = direction
    return await proxy_request(
        method="GET",
        path="friendships",
        headers=request.headers,
        params=params,
        base_url=FRIENDSHIP_SERVICE_URL,
    )


@friendships_read_router.get("/pending", summary="List pending friendship requests")
async def list_pending(request: Request, _: str = Depends(require_bearer_token)):
    """List pending friendship requests for the current user.
    
    Args:
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Pending friendship requests for the current user.
    """
    return await proxy_request(
        method="GET",
        path="friendships/pending",
        headers=request.headers,
        params=request.query_params,
        base_url=FRIENDSHIP_SERVICE_URL,
    )


@friendships_read_router.get("/incoming", summary="List incoming pending friendship requests")
async def list_incoming(request: Request, _: str = Depends(require_bearer_token)):
    """List incoming friendship requests.
    
    Args:
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Incoming friendship requests.
    """
    return await proxy_request(
        method="GET",
        path="friendships/incoming",
        headers=request.headers,
        params=request.query_params,
        base_url=FRIENDSHIP_SERVICE_URL,
    )


@friendships_read_router.get("/outgoing", summary="List outgoing pending friendship requests")
async def list_outgoing(request: Request, _: str = Depends(require_bearer_token)):
    """List outgoing friendship requests.
    
    Args:
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Outgoing friendship requests.
    """
    return await proxy_request(
        method="GET",
        path="friendships/outgoing",
        headers=request.headers,
        params=request.query_params,
        base_url=FRIENDSHIP_SERVICE_URL,
    )
