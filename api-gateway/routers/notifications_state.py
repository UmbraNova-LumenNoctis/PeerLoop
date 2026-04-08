"""Notification mutation proxy routes."""

from fastapi import APIRouter, Depends, Request

from routers.auth import NOTIFICATION_SERVICE_URL, proxy_request
from routers.security import require_bearer_token

notifications_state_router = APIRouter()


@notifications_state_router.patch("/read-all", summary="Mark all my notifications as read")
async def mark_all_read(request: Request, _: str = Depends(require_bearer_token)):
    """Mark all unread notifications as read.
    
    Args:
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Result of the operation.
    """
    return await proxy_request(
        method="PATCH",
        path="notifications/read-all",
        headers=request.headers,
        params=request.query_params,
        base_url=NOTIFICATION_SERVICE_URL,
    )


@notifications_state_router.patch("/{notification_id}/read", summary="Mark notification as read")
async def mark_read(notification_id: str, request: Request, _: str = Depends(require_bearer_token)):
    """Mark one notification as read.
    
    Args:
        notification_id (str): Identifier for notification.
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Result of the operation.
    """
    return await proxy_request(
        method="PATCH",
        path=f"notifications/{notification_id}/read",
        headers=request.headers,
        params=request.query_params,
        base_url=NOTIFICATION_SERVICE_URL,
    )


@notifications_state_router.patch("/{notification_id}/unread", summary="Mark notification as unread")
async def mark_unread(notification_id: str, request: Request, _: str = Depends(require_bearer_token)):
    """Mark one notification as unread.
    
    Args:
        notification_id (str): Identifier for notification.
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Result of the operation.
    """
    return await proxy_request(
        method="PATCH",
        path=f"notifications/{notification_id}/unread",
        headers=request.headers,
        params=request.query_params,
        base_url=NOTIFICATION_SERVICE_URL,
    )


@notifications_state_router.delete("/{notification_id}", summary="Delete my notification")
async def delete_notification(notification_id: str, request: Request, _: str = Depends(require_bearer_token)):
    """Delete one notification owned by current user.
    
    Args:
        notification_id (str): Identifier for notification.
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Result of the operation.
    """
    return await proxy_request(
        method="DELETE",
        path=f"notifications/{notification_id}",
        headers=request.headers,
        params=request.query_params,
        base_url=NOTIFICATION_SERVICE_URL,
    )
