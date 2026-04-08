from fastapi import APIRouter, Depends, Query, Request

from routers.auth import SEARCH_SERVICE_URL, proxy_request
from routers.security import require_bearer_token


search_router = APIRouter(prefix="/api/search", tags=["Search"])


@search_router.get("/users", summary="Search users")
async def search_users(
    request: Request,
    q: str = Query(..., min_length=1, max_length=120),
    limit: int = Query(default=20, ge=1, le=100),
    _: str = Depends(require_bearer_token),
):
    """Proxy user search queries to the search service.
    
    Args:
        request (Request): Incoming FastAPI request context.
        q (str): Search query string.
        limit (int): Maximum number of items to return.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Result of the operation.
    """
    params = dict(request.query_params)
    params["q"] = q.strip()
    params["limit"] = str(limit)

    return await proxy_request(
        method="GET",
        path="search/users",
        headers=request.headers,
        params=params,
        base_url=SEARCH_SERVICE_URL,
    )


@search_router.get("/posts", summary="Search posts")
async def search_posts(
    request: Request,
    q: str = Query(..., min_length=1, max_length=120),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: str = Depends(require_bearer_token),
):
    """Proxy post search queries to the search service.
    
    Args:
        request (Request): Incoming FastAPI request context.
        q (str): Search query string.
        limit (int): Maximum number of items to return.
        offset (int): Pagination offset.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Result of the operation.
    """
    params = dict(request.query_params)
    params["q"] = q.strip()
    params["limit"] = str(limit)
    params["offset"] = str(offset)

    return await proxy_request(
        method="GET",
        path="search/posts",
        headers=request.headers,
        params=params,
        base_url=SEARCH_SERVICE_URL,
    )
