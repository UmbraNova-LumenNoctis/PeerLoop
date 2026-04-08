"""Post and comment write routes."""

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import Response

from routers.auth import POST_SERVICE_URL, proxy_request
from routers.security import require_bearer_token
from shared_schemas.models import (
    CommentCreateRequest,
    CommentUpdateRequest,
    PostCreateRequest,
    PostUpdateRequest,
)

post_write_router = APIRouter()


@post_write_router.post("", status_code=201, summary="Create post")
async def create_post(
    request: Request,
    payload: PostCreateRequest = Body(...),
    _: str = Depends(require_bearer_token),
) -> Response:
    """Create a new post.
    
    Args:
        request (Request): Incoming FastAPI request context.
        payload (PostCreateRequest): Parsed request payload.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Response: New post.
    """
    return await proxy_request(
        method="POST",
        path="posts",
        json_body=payload.model_dump(mode="json", exclude_unset=True, exclude_none=True),
        headers=request.headers,
        params=request.query_params,
        base_url=POST_SERVICE_URL,
    )


@post_write_router.patch("/{post_id}", summary="Update my post")
async def update_post(
    post_id: str,
    request: Request,
    payload: PostUpdateRequest = Body(...),
    _: str = Depends(require_bearer_token),
) -> Response:
    """Update an existing post owned by the current user.
    
    Args:
        post_id (str): Post identifier.
        request (Request): Incoming FastAPI request context.
        payload (PostUpdateRequest): Parsed request payload.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Response: Result of the operation.
    """
    return await proxy_request(
        method="PATCH",
        path=f"posts/{post_id}",
        json_body=payload.model_dump(mode="json", exclude_unset=True),
        headers=request.headers,
        params=request.query_params,
        base_url=POST_SERVICE_URL,
    )


@post_write_router.delete("/{post_id}", summary="Delete my post")
async def delete_post(
    post_id: str,
    request: Request,
    _: str = Depends(require_bearer_token),
) -> Response:
    """Delete one post owned by the current user.
    
    Args:
        post_id (str): Post identifier.
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Response: Result of the operation.
    """
    return await proxy_request(
        method="DELETE",
        path=f"posts/{post_id}",
        headers=request.headers,
        params=request.query_params,
        base_url=POST_SERVICE_URL,
    )


@post_write_router.post("/{post_id}/comments", status_code=201, summary="Create comment on a post")
async def create_comment(
    post_id: str,
    request: Request,
    payload: CommentCreateRequest = Body(...),
    _: str = Depends(require_bearer_token),
) -> Response:
    """Create a comment on a given post.
    
    Args:
        post_id (str): Post identifier.
        request (Request): Incoming FastAPI request context.
        payload (CommentCreateRequest): Parsed request payload.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Response: Comment on a given post.
    """
    return await proxy_request(
        method="POST",
        path=f"posts/{post_id}/comments",
        json_body=payload.model_dump(mode="json", exclude_unset=True),
        headers=request.headers,
        params=request.query_params,
        base_url=POST_SERVICE_URL,
    )


@post_write_router.patch("/comments/{comment_id}", summary="Update my comment")
async def update_comment(
    comment_id: str,
    request: Request,
    payload: CommentUpdateRequest = Body(...),
    _: str = Depends(require_bearer_token),
) -> Response:
    """Update one comment owned by the current user.
    
    Args:
        comment_id (str): Comment identifier.
        request (Request): Incoming FastAPI request context.
        payload (CommentUpdateRequest): Parsed request payload.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Response: Result of the operation.
    """
    return await proxy_request(
        method="PATCH",
        path=f"posts/comments/{comment_id}",
        json_body=payload.model_dump(mode="json", exclude_unset=True),
        headers=request.headers,
        params=request.query_params,
        base_url=POST_SERVICE_URL,
    )
