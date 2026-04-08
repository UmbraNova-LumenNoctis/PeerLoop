"""Read endpoints for posts and feed."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Path, Query

from core.auth import require_current_user
from schemas.models import PostFeedResponse, PostResponse
from serializers.post_serializer import serialize_post_rows
from services.post_feed import load_posts_rows, validate_feed_filters
from stores.post_store import get_post_by_id

post_read_router = APIRouter()


def _load_posts_for_response(
    current_user_id: str,
    user_id: UUID | None,
    friend_only: bool,
    include_self: bool,
    sort_by: str,
    order: str,
    created_before: datetime | None,
    created_after: datetime | None,
    limit: int,
    offset: int,
) -> tuple[list[PostResponse], bool]:
    """Load and serialize posts with shared filtering logic.
    
    Args:
        current_user_id (str): Identifier for current user.
        user_id (UUID | None): User identifier.
        friend_only (bool): Parameter friend_only.
        include_self (bool): Flag controlling whether to self.
        sort_by (str): Parameter sort_by.
        order (str): Parameter order.
        created_before (datetime | None): Parameter created_before.
        created_after (datetime | None): Parameter created_after.
        limit (int): Maximum number of items to return.
        offset (int): Pagination offset.
    
    Returns:
        tuple[list[PostResponse], bool]: Retrieved value.
    """
    rows, has_more = load_posts_rows(
        current_user_id=current_user_id,
        user_id=str(user_id) if user_id else None,
        friend_only=friend_only,
        include_self=include_self,
        sort_by=sort_by,
        order=order,
        limit=limit,
        offset=offset,
        created_before=created_before,
        created_after=created_after,
    )
    return serialize_post_rows(rows, current_user_id), has_more


@post_read_router.get("", response_model=list[PostResponse], summary="List posts")
def list_posts(
    user_id: UUID | None = Query(default=None),
    friend_only: bool = Query(default=False),
    include_self: bool = Query(default=True),
    sort_by: Literal["created_at", "updated_at", "popularity"] = Query(default="created_at"),
    order: Literal["asc", "desc"] = Query(default="desc"),
    created_before: datetime | None = Query(default=None),
    created_after: datetime | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """List posts with optional filters, sorting and pagination.
    
    Args:
        user_id (UUID | None): User identifier.
        friend_only (bool): Parameter friend_only.
        include_self (bool): Flag controlling whether to self.
        sort_by (Literal['created_at', 'updated_at', 'popularity']): Parameter sort_by.
        order (Literal['asc', 'desc']): Parameter order.
        created_before (datetime | None): Parameter created_before.
        created_after (datetime | None): Parameter created_after.
        limit (int): Maximum number of items to return.
        offset (int): Pagination offset.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Posts with optional filters, sorting and pagination.
    """
    current_user_id = require_current_user(x_user_id, x_access_token)
    validate_feed_filters(user_id, friend_only, created_before, created_after)
    items, _ = _load_posts_for_response(
        current_user_id,
        user_id,
        friend_only,
        include_self,
        sort_by,
        order,
        created_before,
        created_after,
        limit,
        offset,
    )
    return items


@post_read_router.get("/feed", response_model=PostFeedResponse, summary="Feed with advanced pagination")
def get_feed(
    user_id: UUID | None = Query(default=None),
    friend_only: bool = Query(default=False),
    include_self: bool = Query(default=True),
    sort_by: Literal["created_at", "updated_at", "popularity"] = Query(default="created_at"),
    order: Literal["asc", "desc"] = Query(default="desc"),
    created_before: datetime | None = Query(default=None),
    created_after: datetime | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Return feed payload including has_more and next_offset.
    
    Args:
        user_id (UUID | None): User identifier.
        friend_only (bool): Parameter friend_only.
        include_self (bool): Flag controlling whether to self.
        sort_by (Literal['created_at', 'updated_at', 'popularity']): Parameter sort_by.
        order (Literal['asc', 'desc']): Parameter order.
        created_before (datetime | None): Parameter created_before.
        created_after (datetime | None): Parameter created_after.
        limit (int): Maximum number of items to return.
        offset (int): Pagination offset.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Feed payload including has_more and next_offset.
    """
    current_user_id = require_current_user(x_user_id, x_access_token)
    validate_feed_filters(user_id, friend_only, created_before, created_after)
    items, has_more = _load_posts_for_response(
        current_user_id,
        user_id,
        friend_only,
        include_self,
        sort_by,
        order,
        created_before,
        created_after,
        limit,
        offset,
    )
    return PostFeedResponse(
        items=items,
        limit=limit,
        offset=offset,
        returned=len(items),
        has_more=has_more,
        next_offset=(offset + len(items)) if has_more else None,
    )


@post_read_router.get("/{post_id}", response_model=PostResponse, summary="Get post by id")
def get_post(
    post_id: UUID = Path(...),
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Return one post by id.
    
    Args:
        post_id (UUID): Post identifier.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: One post by id.
    """
    current_user_id = require_current_user(x_user_id, x_access_token)
    row = get_post_by_id(str(post_id))
    if not row:
        raise HTTPException(status_code=404, detail="Post not found")
    return serialize_post_rows([row], current_user_id)[0]
