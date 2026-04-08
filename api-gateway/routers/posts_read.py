"""Read-only post and comment routes."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from routers.auth import POST_SERVICE_URL, proxy_request
from routers.security import require_bearer_token

post_read_router = APIRouter()


def _build_feed_params(
    request: Request,
    user_id: str | None,
    friend_only: bool,
    include_self: bool,
    sort_by: Literal["created_at", "updated_at", "popularity"],
    order: Literal["asc", "desc"],
    created_before: datetime | None,
    created_after: datetime | None,
    limit: int,
    offset: int,
) -> dict[str, str]:
    """Build normalized query params for list/feed endpoints.
    
    Args:
        request (Request): Incoming FastAPI request context.
        user_id (str | None): User identifier.
        friend_only (bool): Parameter friend_only.
        include_self (bool): Flag controlling whether to self.
        sort_by (Literal['created_at', 'updated_at', 'popularity']): Parameter sort_by.
        order (Literal['asc', 'desc']): Parameter order.
        created_before (datetime | None): Parameter created_before.
        created_after (datetime | None): Parameter created_after.
        limit (int): Maximum number of items to return.
        offset (int): Pagination offset.
    
    Returns:
        dict[str, str]: Normalized query params for list/feed endpoints.
    """
    params = dict(request.query_params)
    if user_id is not None:
        params["user_id"] = user_id

    params["friend_only"] = str(friend_only).lower()
    params["include_self"] = str(include_self).lower()
    params["sort_by"] = sort_by
    params["order"] = order
    params["limit"] = str(limit)
    params["offset"] = str(offset)

    if created_before is not None:
        params["created_before"] = created_before.isoformat()
    if created_after is not None:
        params["created_after"] = created_after.isoformat()

    return params


@post_read_router.get("", summary="List posts")
async def list_posts(
    request: Request,
    user_id: str | None = Query(default=None),
    friend_only: bool = Query(default=False),
    include_self: bool = Query(default=True),
    sort_by: Literal["created_at", "updated_at", "popularity"] = Query(default="created_at"),
    order: Literal["asc", "desc"] = Query(default="desc"),
    created_before: datetime | None = Query(default=None),
    created_after: datetime | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: str = Depends(require_bearer_token),
) -> Response:
    """List posts with optional filtering and pagination.
    
    Args:
        request (Request): Incoming FastAPI request context.
        user_id (str | None): User identifier.
        friend_only (bool): Parameter friend_only.
        include_self (bool): Flag controlling whether to self.
        sort_by (Literal['created_at', 'updated_at', 'popularity']): Parameter sort_by.
        order (Literal['asc', 'desc']): Parameter order.
        created_before (datetime | None): Parameter created_before.
        created_after (datetime | None): Parameter created_after.
        limit (int): Maximum number of items to return.
        offset (int): Pagination offset.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Response: Posts with optional filtering and pagination.
    """
    params = _build_feed_params(
        request=request,
        user_id=user_id,
        friend_only=friend_only,
        include_self=include_self,
        sort_by=sort_by,
        order=order,
        created_before=created_before,
        created_after=created_after,
        limit=limit,
        offset=offset,
    )
    return await proxy_request(
        method="GET",
        path="posts",
        headers=request.headers,
        params=params,
        base_url=POST_SERVICE_URL,
    )


@post_read_router.get("/feed", summary="Feed with advanced pagination")
async def get_feed(
    request: Request,
    user_id: str | None = Query(default=None),
    friend_only: bool = Query(default=False),
    include_self: bool = Query(default=True),
    sort_by: Literal["created_at", "updated_at", "popularity"] = Query(default="created_at"),
    order: Literal["asc", "desc"] = Query(default="desc"),
    created_before: datetime | None = Query(default=None),
    created_after: datetime | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: str = Depends(require_bearer_token),
) -> Response:
    """Get personalized feed with advanced pagination and sorting.
    
    Args:
        request (Request): Incoming FastAPI request context.
        user_id (str | None): User identifier.
        friend_only (bool): Parameter friend_only.
        include_self (bool): Flag controlling whether to self.
        sort_by (Literal['created_at', 'updated_at', 'popularity']): Parameter sort_by.
        order (Literal['asc', 'desc']): Parameter order.
        created_before (datetime | None): Parameter created_before.
        created_after (datetime | None): Parameter created_after.
        limit (int): Maximum number of items to return.
        offset (int): Pagination offset.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Response: Personalized feed with advanced pagination and sorting.
    """
    params = _build_feed_params(
        request=request,
        user_id=user_id,
        friend_only=friend_only,
        include_self=include_self,
        sort_by=sort_by,
        order=order,
        created_before=created_before,
        created_after=created_after,
        limit=limit,
        offset=offset,
    )
    return await proxy_request(
        method="GET",
        path="posts/feed",
        headers=request.headers,
        params=params,
        base_url=POST_SERVICE_URL,
    )


@post_read_router.get("/{post_id}", summary="Get post by id")
async def get_post(
    post_id: str,
    request: Request,
    _: str = Depends(require_bearer_token),
) -> Response:
    """Get one post by identifier.
    
    Args:
        post_id (str): Post identifier.
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Response: One post by identifier.
    """
    return await proxy_request(
        method="GET",
        path=f"posts/{post_id}",
        headers=request.headers,
        params=request.query_params,
        base_url=POST_SERVICE_URL,
    )


@post_read_router.get("/{post_id}/comments", summary="List comments of a post")
async def list_comments(
    post_id: str,
    request: Request,
    _: str = Depends(require_bearer_token),
) -> Response:
    """List comments attached to one post.
    
    Args:
        post_id (str): Post identifier.
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Response: Comments attached to one post.
    """
    return await proxy_request(
        method="GET",
        path=f"posts/{post_id}/comments",
        headers=request.headers,
        params=request.query_params,
        base_url=POST_SERVICE_URL,
    )
