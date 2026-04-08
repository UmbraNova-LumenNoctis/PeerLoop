"""Search routes for users and posts endpoints."""

from fastapi import APIRouter, Header, Query

from ..core.auth_utils import require_authenticated_user
from ..core.context import DEFAULT_AVATAR_URL
from ..services.post_search import search_posts_raw
from ..schemas.search_models import SearchPostsResponse, SearchUsersResponse
from ..services.user_search import search_users_raw

search_router = APIRouter(prefix="/search", tags=["Search"])


@search_router.get("/users", response_model=SearchUsersResponse, summary="Search users")
def search_users(
    q: str = Query(..., min_length=1, max_length=120, description="Search by pseudo or email"),
    limit: int = Query(default=20, ge=1, le=100),
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Search users by pseudo, email and bio.
    
    Args:
        q (str): Search query string.
        limit (int): Maximum number of items to return.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Result of the operation.
    """
    require_authenticated_user(x_user_id, x_access_token)
    items = search_users_raw(q, limit=limit, default_avatar_url=DEFAULT_AVATAR_URL)
    return SearchUsersResponse(query=q, limit=limit, total=len(items), items=items)


@search_router.get("/posts", response_model=SearchPostsResponse, summary="Search posts")
def search_posts(
    q: str = Query(..., min_length=1, max_length=120, description="Search posts by content or author"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Search posts by text content and matching author identity.
    
    Args:
        q (str): Search query string.
        limit (int): Maximum number of items to return.
        offset (int): Pagination offset.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Result of the operation.
    """
    current_user_id = require_authenticated_user(x_user_id, x_access_token)
    items, total = search_posts_raw(
        q,
        limit=limit,
        offset=offset,
        current_user_id=current_user_id,
        default_avatar_url=DEFAULT_AVATAR_URL,
    )
    return SearchPostsResponse(query=q, limit=limit, offset=offset, total=total, items=items)
