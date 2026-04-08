"""Mutation routes for notifications."""

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Path
from postgrest.exceptions import APIError

from core.context import NOTIFICATIONS_TABLE, require_supabase
from schemas.models import NotificationCreateRequest, NotificationResponse
from core.security import is_internal_token_valid, resolve_user_id
from stores.storage import get_notification_row, require_notification_owner, serialize_notification_row

notification_write_router = APIRouter()


@notification_write_router.post(
    "/internal",
    response_model=NotificationResponse,
    status_code=201,
    summary="Create notification for any user (internal services)",
)
def create_internal_notification(payload: NotificationCreateRequest, x_internal_service_token: str = Header(None)):
    """Create notification for arbitrary user from trusted internal services.
    
    Args:
        payload (NotificationCreateRequest): Parsed request payload.
        x_internal_service_token (str): Parameter x_internal_service_token.
    
    Returns:
        Any: Notification for arbitrary user from trusted internal services.
    """
    if not is_internal_token_valid(x_internal_service_token):
        raise HTTPException(status_code=401, detail="Unauthorized internal request")
    if not payload.user_id:
        raise HTTPException(status_code=422, detail="user_id is required for internal notification creation")

    payload_dict = {
        "user_id": str(payload.user_id),
        "type": payload.type.strip(),
        "content": payload.content,
        "source_id": str(payload.source_id) if payload.source_id else None,
        "actor_id": str(payload.actor_id) if payload.actor_id else None,
        "is_read": False,
    }

    try:
        created = require_supabase().table(NOTIFICATIONS_TABLE).insert(payload_dict).execute()
    except APIError as exc:
        # Backward compatibility: old DB schema may not yet contain actor_id.
        exc_text = str(exc)
        if "actor_id" in exc_text:
            payload_dict.pop("actor_id", None)
            try:
                created = require_supabase().table(NOTIFICATIONS_TABLE).insert(payload_dict).execute()
            except APIError as fallback_exc:
                raise HTTPException(status_code=502, detail=f"Notification creation failed: {fallback_exc}") from fallback_exc
        else:
            raise HTTPException(status_code=502, detail=f"Notification creation failed: {exc}") from exc

    rows = created.data or []
    if not rows:
        raise HTTPException(status_code=502, detail="Notification was created but not returned")
    return serialize_notification_row(rows[0])


@notification_write_router.patch("/read-all", summary="Mark all my notifications as read")
def mark_all_read(x_user_id: str = Header(None), x_access_token: str = Header(None)):
    """Mark all unread notifications for current user as read.
    
    Args:
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Result of the operation.
    """
    current_user_id = resolve_user_id(x_user_id, x_access_token)
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: missing or invalid access token")

    try:
        updated = (
            require_supabase()
            .table(NOTIFICATIONS_TABLE)
            .update({"is_read": True})
            .eq("user_id", current_user_id)
            .eq("is_read", False)
            .execute()
        )
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Mark all read failed: {exc}") from exc

    return {"message": "All notifications marked as read", "updated_count": len(updated.data or [])}


@notification_write_router.patch("/{notification_id}/read", response_model=NotificationResponse, summary="Mark as read")
def mark_read(
    notification_id: UUID = Path(...),
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Mark one notification as read.
    
    Args:
        notification_id (UUID): Identifier for notification.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Result of the operation.
    """
    current_user_id = resolve_user_id(x_user_id, x_access_token)
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: missing or invalid access token")

    require_notification_owner(str(notification_id), current_user_id)
    try:
        updated = require_supabase().table(NOTIFICATIONS_TABLE).update({"is_read": True}).eq("id", str(notification_id)).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Mark read failed: {exc}") from exc

    rows = updated.data or []
    row = rows[0] if rows else get_notification_row(str(notification_id))
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found")
    return serialize_notification_row(row)


@notification_write_router.patch("/{notification_id}/unread", response_model=NotificationResponse, summary="Mark as unread")
def mark_unread(
    notification_id: UUID = Path(...),
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Mark one notification as unread.
    
    Args:
        notification_id (UUID): Identifier for notification.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Result of the operation.
    """
    current_user_id = resolve_user_id(x_user_id, x_access_token)
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: missing or invalid access token")

    require_notification_owner(str(notification_id), current_user_id)
    try:
        updated = require_supabase().table(NOTIFICATIONS_TABLE).update({"is_read": False}).eq("id", str(notification_id)).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Mark unread failed: {exc}") from exc

    rows = updated.data or []
    row = rows[0] if rows else get_notification_row(str(notification_id))
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found")
    return serialize_notification_row(row)


@notification_write_router.delete("/{notification_id}", summary="Delete my notification")
def delete_notification(
    notification_id: UUID = Path(...),
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Delete one notification owned by current user.
    
    Args:
        notification_id (UUID): Identifier for notification.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Result of the operation.
    """
    current_user_id = resolve_user_id(x_user_id, x_access_token)
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: missing or invalid access token")

    require_notification_owner(str(notification_id), current_user_id)
    try:
        require_supabase().table(NOTIFICATIONS_TABLE).delete().eq("id", str(notification_id)).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Notification delete failed: {exc}") from exc

    return {"message": "Notification deleted", "notification_id": str(notification_id)}
