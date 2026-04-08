"""Write endpoints for friendship service."""

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Path
from postgrest.exceptions import APIError

from core.auth_utils import require_current_user
from core.context import STATUS_ACCEPTED, STATUS_BLOCKED, STATUS_PENDING, require_supabase
from serializers.friendship_serialize import serialize_friendship_for_user
from stores.friendship_store import (
    ensure_participant,
    get_friendship_between,
    get_friendship_by_id,
    update_friendship_status,
)
from schemas.models import FriendshipCreateRequest, FriendshipResponse
from services.notifications import send_notification
from stores.user_store import resolve_target_user

friendship_write_router = APIRouter()


@friendship_write_router.post(
    "/request",
    response_model=FriendshipResponse,
    status_code=201,
    summary="Send friendship request",
)
def send_friend_request(
    payload: FriendshipCreateRequest,
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Create one pending friendship request.
    
    Args:
        payload (FriendshipCreateRequest): Parsed request payload.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: One pending friendship request.
    """
    current_user_id = require_current_user(x_user_id, x_access_token)

    target_user = resolve_target_user(payload)
    target_user_id = str(target_user.get("id"))
    if target_user_id == current_user_id:
        raise HTTPException(status_code=400, detail="Cannot create friendship with yourself")

    existing = get_friendship_between(current_user_id, target_user_id)
    if existing:
        status = (existing.get("status") or "").lower()
        if status == STATUS_ACCEPTED:
            raise HTTPException(status_code=409, detail="Users are already friends")
        if status == STATUS_PENDING:
            raise HTTPException(status_code=409, detail="Friendship request already pending")
        if status == STATUS_BLOCKED:
            raise HTTPException(status_code=403, detail="Friendship is blocked")
        raise HTTPException(status_code=409, detail="Friendship already exists")

    try:
        created = (
            require_supabase()
            .table("friendships")
            .insert({"user_a_id": current_user_id, "user_b_id": target_user_id, "status": STATUS_PENDING})
            .execute()
        )
    except APIError as exc:
        if "duplicate" in str(exc).lower():
            raise HTTPException(status_code=409, detail="Friendship already exists")
        raise HTTPException(status_code=502, detail=f"Friendship creation failed: {exc}") from exc

    rows = created.data or []
    row = rows[0] if rows else get_friendship_between(current_user_id, target_user_id)
    if not row:
        raise HTTPException(status_code=502, detail="Friendship was created but not returned")

    source_id = str(row.get("id")) if row.get("id") else None
    send_notification(
        target_user_id=target_user_id,
        notification_type="friend_request",
        content="You have a new friend request",
        source_id=source_id,
    )
    send_notification(
        target_user_id=current_user_id,
        notification_type="friendship_created",
        content="Friend request sent",
        source_id=source_id,
    )
    return serialize_friendship_for_user(row, current_user_id)


@friendship_write_router.patch(
    "/{friendship_id}/accept",
    response_model=FriendshipResponse,
    summary="Accept friendship",
)
def accept_friendship(
    friendship_id: UUID = Path(...),
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Accept one pending friendship as request recipient.
    
    Args:
        friendship_id (UUID): Identifier for friendship.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Result of the operation.
    """
    current_user_id = require_current_user(x_user_id, x_access_token)

    row = get_friendship_by_id(str(friendship_id))
    if not row:
        raise HTTPException(status_code=404, detail="Friendship not found")
    ensure_participant(row, current_user_id)

    status = (row.get("status") or "").lower()
    accepted_now = False

    if status == STATUS_BLOCKED:
        raise HTTPException(status_code=409, detail="Blocked friendship cannot be accepted")
    if status == STATUS_PENDING:
        if str(row.get("user_b_id")) != current_user_id:
            raise HTTPException(status_code=403, detail="Only recipient can accept pending friendship")
        row = update_friendship_status(str(friendship_id), STATUS_ACCEPTED)
        accepted_now = True
    elif status != STATUS_ACCEPTED:
        raise HTTPException(status_code=409, detail=f"Cannot accept friendship in status '{status or 'unknown'}'")

    if accepted_now:
        requester_id = str(row.get("user_a_id"))
        if requester_id != current_user_id:
            send_notification(
                target_user_id=requester_id,
                notification_type="friend_accept",
                content="Your friend request was accepted",
                source_id=str(friendship_id),
            )
        send_notification(
            target_user_id=current_user_id,
            notification_type="friendship_updated",
            content="Friend request accepted",
            source_id=str(friendship_id),
        )

    return serialize_friendship_for_user(row, current_user_id)


@friendship_write_router.patch(
    "/{friendship_id}/block",
    response_model=FriendshipResponse,
    summary="Block friendship",
)
def block_friendship(
    friendship_id: UUID = Path(...),
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Block one friendship.
    
    Args:
        friendship_id (UUID): Identifier for friendship.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Result of the operation.
    """
    current_user_id = require_current_user(x_user_id, x_access_token)

    row = get_friendship_by_id(str(friendship_id))
    if not row:
        raise HTTPException(status_code=404, detail="Friendship not found")
    ensure_participant(row, current_user_id)

    blocked_now = False
    if (row.get("status") or "").lower() != STATUS_BLOCKED:
        row = update_friendship_status(str(friendship_id), STATUS_BLOCKED)
        blocked_now = True

    if blocked_now:
        other_user_id = (
            str(row.get("user_b_id"))
            if str(row.get("user_a_id")) == current_user_id
            else str(row.get("user_a_id"))
        )
        if other_user_id != current_user_id:
            send_notification(
                target_user_id=other_user_id,
                notification_type="friendship_blocked",
                content="A friendship was blocked",
                source_id=str(friendship_id),
            )
        send_notification(
            target_user_id=current_user_id,
            notification_type="friendship_updated",
            content="Friendship blocked",
            source_id=str(friendship_id),
        )

    return serialize_friendship_for_user(row, current_user_id)


@friendship_write_router.delete("/{friendship_id}", summary="Delete friendship")
def delete_friendship(
    friendship_id: UUID = Path(...),
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Delete one friendship for either participant.
    
    Args:
        friendship_id (UUID): Identifier for friendship.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Result of the operation.
    """
    current_user_id = require_current_user(x_user_id, x_access_token)

    row = get_friendship_by_id(str(friendship_id))
    if not row:
        raise HTTPException(status_code=404, detail="Friendship not found")
    ensure_participant(row, current_user_id)

    try:
        require_supabase().table("friendships").delete().eq("id", str(friendship_id)).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Friendship delete failed: {exc}") from exc

    other_user_id = (
        str(row.get("user_b_id"))
        if str(row.get("user_a_id")) == current_user_id
        else str(row.get("user_a_id"))
    )
    if other_user_id != current_user_id:
        send_notification(
            target_user_id=other_user_id,
            notification_type="friendship_deleted",
            content="A friendship was removed",
            source_id=str(friendship_id),
        )
    send_notification(
        target_user_id=current_user_id,
        notification_type="friendship_deleted",
        content="Friendship deleted",
        source_id=str(friendship_id),
    )

    return {"message": "Friendship deleted", "friendship_id": str(friendship_id)}
