"""Read endpoints for friendship service."""

from fastapi import APIRouter, Header, HTTPException, Query

from core.auth_utils import require_current_user
from core.context import STATUS_PENDING, VALID_DIRECTIONS, VALID_STATUSES
from serializers.friendship_serialize import serialize_friendship_rows
from stores.friendship_store import list_friendship_rows
from schemas.models import FriendshipResponse

friendship_list_router = APIRouter()


@friendship_list_router.get(
    "",
    response_model=list[FriendshipResponse],
    summary="List friendships",
    description="List friendships for current user. Optional filters: status and direction (incoming|outgoing).",
)
def list_friendships(
    status: str | None = Query(default=None),
    direction: str | None = Query(default=None),
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """List friendships for current user with optional filters.
    
    Args:
        status (str | None): Parameter status.
        direction (str | None): Parameter direction.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Friendships for current user with optional filters.
    """
    current_user_id = require_current_user(x_user_id, x_access_token)

    normalized_status = status
    if status is not None:
        normalized_status = status.lower().strip()
        if normalized_status not in VALID_STATUSES:
            raise HTTPException(status_code=422, detail="Invalid status filter")

    normalized_direction = direction
    if direction is not None:
        normalized_direction = direction.lower().strip()
        if normalized_direction not in VALID_DIRECTIONS:
            raise HTTPException(status_code=422, detail="Invalid direction filter")

    rows = list_friendship_rows(current_user_id, status=normalized_status, direction=normalized_direction)
    return serialize_friendship_rows(rows, current_user_id)


@friendship_list_router.get("/pending", response_model=list[FriendshipResponse], summary="List pending requests")
def list_pending_requests(x_user_id: str = Header(None), x_access_token: str = Header(None)):
    """List all pending friendships for current user.
    
    Args:
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: All pending friendships for current user.
    """
    current_user_id = require_current_user(x_user_id, x_access_token)
    rows = list_friendship_rows(current_user_id, status=STATUS_PENDING, direction=None)
    return serialize_friendship_rows(rows, current_user_id)


@friendship_list_router.get(
    "/incoming",
    response_model=list[FriendshipResponse],
    summary="List incoming pending requests",
)
def list_incoming_requests(x_user_id: str = Header(None), x_access_token: str = Header(None)):
    """List incoming pending friendships for current user.
    
    Args:
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Incoming pending friendships for current user.
    """
    current_user_id = require_current_user(x_user_id, x_access_token)
    rows = list_friendship_rows(current_user_id, status=STATUS_PENDING, direction="incoming")
    return serialize_friendship_rows(rows, current_user_id)


@friendship_list_router.get(
    "/outgoing",
    response_model=list[FriendshipResponse],
    summary="List outgoing pending requests",
)
def list_outgoing_requests(x_user_id: str = Header(None), x_access_token: str = Header(None)):
    """List outgoing pending friendships for current user.
    
    Args:
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Outgoing pending friendships for current user.
    """
    current_user_id = require_current_user(x_user_id, x_access_token)
    rows = list_friendship_rows(current_user_id, status=STATUS_PENDING, direction="outgoing")
    return serialize_friendship_rows(rows, current_user_id)
