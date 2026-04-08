"""Post interaction routes (likes and comment deletion)."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from routers.auth import POST_SERVICE_URL, proxy_request
from routers.security import require_bearer_token

post_actions_router = APIRouter()


@post_actions_router.post("/{post_id}/like", summary="Like post")
async def like_post(
    post_id: str,
    request: Request,
    _: str = Depends(require_bearer_token),
) -> Response:
    """Like a post.
    
    Args:
        post_id (str): Post identifier.
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Response: Result of the operation.
    """
    return await proxy_request(
        method="POST",
        path=f"posts/{post_id}/like",
        headers=request.headers,
        params=request.query_params,
        base_url=POST_SERVICE_URL,
    )


@post_actions_router.delete("/{post_id}/like", summary="Unlike post")
async def unlike_post(
    post_id: str,
    request: Request,
    _: str = Depends(require_bearer_token),
) -> Response:
    """Remove current user's like from a post.
    
    Args:
        post_id (str): Post identifier.
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Response: Result of the operation.
    """
    return await proxy_request(
        method="DELETE",
        path=f"posts/{post_id}/like",
        headers=request.headers,
        params=request.query_params,
        base_url=POST_SERVICE_URL,
    )


@post_actions_router.delete(
    "/comments/{comment_id}",
    summary="Delete comment (owner or post owner)",
)
async def delete_comment(
    comment_id: str,
    request: Request,
    _: str = Depends(require_bearer_token),
) -> Response:
    """Delete one comment.
    
    Args:
        comment_id (str): Comment identifier.
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Response: Result of the operation.
    """
    return await proxy_request(
        method="DELETE",
        path=f"posts/comments/{comment_id}",
        headers=request.headers,
        params=request.query_params,
        base_url=POST_SERVICE_URL,
    )
