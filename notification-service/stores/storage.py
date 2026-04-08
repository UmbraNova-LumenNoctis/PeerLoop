"""Storage and serialization helpers for notification rows."""

from fastapi import HTTPException
from postgrest.exceptions import APIError

from core.context import NOTIFICATIONS_TABLE, require_supabase
from schemas.models import NotificationResponse


def serialize_notification_row(row: dict) -> NotificationResponse:
    """Convert raw notification row into API response model.
    
    Args:
        row (dict): Parameter row.
    
    Returns:
        NotificationResponse: Raw notification row into API response model.
    """
    return NotificationResponse(
        id=row.get("id"),
        user_id=row.get("user_id"),
        type=row.get("type"),
        content=row.get("content"),
        source_id=row.get("source_id"),
        actor_id=row.get("actor_id"),
        is_read=bool(row.get("is_read")),
        created_at=row.get("created_at"),
    )


def get_notification_row(notification_id: str) -> dict | None:
    """Fetch one notification row by identifier.
    
    Args:
        notification_id (str): Identifier for notification.
    
    Returns:
        dict | None: One notification row by identifier.
    """
    try:
        result = (
            require_supabase()
            .table(NOTIFICATIONS_TABLE)
            .select("*")
            .eq("id", notification_id)
            .limit(1)
            .execute()
        )
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Notification lookup failed: {exc}") from exc

    rows = result.data or []
    return rows[0] if rows else None


def require_notification_owner(notification_id: str, current_user_id: str) -> dict:
    """Ensure notification exists and belongs to current user.
    
    Args:
        notification_id (str): Identifier for notification.
        current_user_id (str): Identifier for current user.
    
    Returns:
        dict: Notification exists and belongs to current user.
    """
    row = get_notification_row(notification_id)
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found")
    if str(row.get("user_id")) != current_user_id:
        raise HTTPException(status_code=403, detail="Forbidden: notification does not belong to current user")
    return row
