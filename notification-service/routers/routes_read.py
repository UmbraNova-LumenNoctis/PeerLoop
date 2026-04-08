"""Read-only notification routes."""

from fastapi import APIRouter, Header, HTTPException, Query
from postgrest.exceptions import APIError

from core.context import NOTIFICATIONS_TABLE, require_supabase
from schemas.models import NotificationResponse, NotificationUnreadCountResponse
from core.security import resolve_user_id
from stores.storage import serialize_notification_row

notification_read_router = APIRouter()


@notification_read_router.get("", response_model=list[NotificationResponse], summary="List my notifications")
def list_notifications(
    is_read: bool | None = Query(default=None),
    type: str | None = Query(default=None, min_length=1, max_length=64),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    order: str = Query(default="desc"),
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """List current user's notifications with optional filters.
    
    Args:
        is_read (bool | None): Flag indicating whether read.
        type (str | None): Parameter type.
        limit (int): Maximum number of items to return.
        offset (int): Pagination offset.
        order (str): Parameter order.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Current user's notifications with optional filters.
    """
    current_user_id = resolve_user_id(x_user_id, x_access_token)
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: missing or invalid access token")

    normalized_order = order.lower().strip()
    if normalized_order not in {"asc", "desc"}:
        raise HTTPException(status_code=422, detail="Invalid order. Use 'asc' or 'desc'")

    try:
        query = require_supabase().table(NOTIFICATIONS_TABLE).select("*").eq("user_id", current_user_id)
        if is_read is not None:
            query = query.eq("is_read", is_read)
        if type is not None:
            query = query.eq("type", type)
        result = query.order("created_at", desc=(normalized_order == "desc")).range(offset, offset + limit - 1).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Notification list failed: {exc}") from exc

    return [serialize_notification_row(row) for row in (result.data or [])]


@notification_read_router.get(
    "/unread-count",
    response_model=NotificationUnreadCountResponse,
    summary="Get unread count",
)
def get_unread_count(x_user_id: str = Header(None), x_access_token: str = Header(None)):
    """Return unread notification count for current user.
    
    Args:
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Unread notification count for current user.
    """
    current_user_id = resolve_user_id(x_user_id, x_access_token)
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: missing or invalid access token")

    try:
        result = (
            require_supabase()
            .table(NOTIFICATIONS_TABLE)
            .select("id")
            .eq("user_id", current_user_id)
            .eq("is_read", False)
            .execute()
        )
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Unread count lookup failed: {exc}") from exc

    return NotificationUnreadCountResponse(unread_count=len(result.data or []))
