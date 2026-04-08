"""Read-only notification proxy routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from routers.auth import NOTIFICATION_SERVICE_URL, proxy_request
from routers.security import require_bearer_token

notifications_read_router = APIRouter()


@notifications_read_router.get("", summary="List my notifications")
async def list_notifications(
    request: Request,
    is_read: bool | None = Query(default=None),
    type: str | None = Query(default=None, min_length=1, max_length=64),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    order: str = Query(default="desc"),
    _: str = Depends(require_bearer_token),
):
    """List current user notifications with pagination and filters.
    
    Args:
        request (Request): Incoming FastAPI request context.
        is_read (bool | None): Flag indicating whether read.
        type (str | None): Parameter type.
        limit (int): Maximum number of items to return.
        offset (int): Pagination offset.
        order (str): Parameter order.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Current user notifications with pagination and filters.
    """
    params = dict(request.query_params)
    if is_read is not None:
        params["is_read"] = str(is_read).lower()
    if type is not None:
        params["type"] = type
    params["limit"] = str(limit)
    params["offset"] = str(offset)
    params["order"] = order
    return await proxy_request(
        method="GET",
        path="notifications",
        headers=request.headers,
        params=params,
        base_url=NOTIFICATION_SERVICE_URL,
    )


@notifications_read_router.get("/unread-count", summary="Get unread count")
async def get_unread_count(request: Request, _: str = Depends(require_bearer_token)):
    """Get unread notification count, returning 0 on upstream transient failure.
    
    Args:
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Unread notification count, returning 0 on upstream transient failure.
    """
    try:
        return await proxy_request(
            method="GET",
            path="notifications/unread-count",
            headers=request.headers,
            params=request.query_params,
            base_url=NOTIFICATION_SERVICE_URL,
        )
    except HTTPException as exc:
        if exc.status_code == 502:
            return JSONResponse(content={"unread_count": 0}, status_code=200)
        raise
