"""Comment endpoints for post service."""

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException

from core.auth import require_current_user
from schemas.models import CommentCreateRequest, CommentResponse, CommentUpdateRequest
from serializers.comment_serializer import serialize_comment_rows
from services.notifications import send_notification
from stores.comment_store import (
    create_comment_row,
    delete_comments_by_ids,
    get_comment_by_id,
    list_comment_rows_for_post,
    update_comment_content,
)
from stores.comment_thread import collect_comment_thread_ids
from stores.post_store import get_post_by_id
from utils.content import normalize_content

comment_router = APIRouter()


def _get_existing_post(post_id: str) -> dict:
    """Fetch post row or raise 404.
    
    Args:
        post_id (str): Post identifier.
    
    Returns:
        dict: Post row or raise 404.
    """
    post_row = get_post_by_id(post_id)
    if not post_row:
        raise HTTPException(status_code=404, detail="Post not found")
    return post_row


@comment_router.get("/{post_id}/comments", response_model=list[CommentResponse], summary="List comments for a post")
def list_post_comments(
    post_id: UUID,
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """List comments for one post.
    
    Args:
        post_id (UUID): Post identifier.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Comments for one post.
    """
    require_current_user(x_user_id, x_access_token)
    _get_existing_post(str(post_id))
    return serialize_comment_rows(list_comment_rows_for_post(str(post_id)))


@comment_router.post("/{post_id}/comments", response_model=CommentResponse, status_code=201, summary="Add comment on a post")
def create_comment(
    post_id: UUID,
    payload: CommentCreateRequest,
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Create one comment on a post or as reply to an existing comment.
    
    Args:
        post_id (UUID): Post identifier.
        payload (CommentCreateRequest): Parsed request payload.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: One comment on a post or as reply to an existing comment.
    """
    current_user_id = require_current_user(x_user_id, x_access_token)
    post_row = _get_existing_post(str(post_id))

    content = normalize_content(payload.content)
    if not content:
        raise HTTPException(status_code=422, detail="Comment content cannot be empty")

    parent_comment_id = str(payload.parent_comment_id) if payload.parent_comment_id else None
    if parent_comment_id:
        parent_comment = get_comment_by_id(parent_comment_id)
        if not parent_comment:
            raise HTTPException(status_code=404, detail="Parent comment not found")
        if str(parent_comment.get("post_id")) != str(post_id):
            raise HTTPException(status_code=409, detail="Parent comment must belong to the same post")

    comment_row = create_comment_row(str(post_id), current_user_id, content, parent_comment_id)
    comment_id = str(comment_row.get("id")) if comment_row.get("id") else None
    send_notification(
        target_user_id=current_user_id,
        notification_type="comment_created",
        content="Your comment was created",
        source_id=comment_id or str(post_id),
    )

    post_owner_id = str(post_row.get("user_id"))
    if post_owner_id != current_user_id:
        send_notification(
            target_user_id=post_owner_id,
            notification_type="post_comment",
            content="Someone commented on your post",
            # Keep actor id in source_id for backward compatibility when
            # notifications.actor_id column is not yet migrated.
            source_id=current_user_id,
            actor_id=current_user_id,
        )

    return serialize_comment_rows([comment_row])[0]


@comment_router.patch("/comments/{comment_id}", response_model=CommentResponse, summary="Update my comment")
def update_comment(
    comment_id: UUID,
    payload: CommentUpdateRequest,
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Update one comment owned by current user.
    
    Args:
        comment_id (UUID): Comment identifier.
        payload (CommentUpdateRequest): Parsed request payload.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Result of the operation.
    """
    current_user_id = require_current_user(x_user_id, x_access_token)

    comment_row = get_comment_by_id(str(comment_id))
    if not comment_row:
        raise HTTPException(status_code=404, detail="Comment not found")
    if str(comment_row.get("user_id")) != current_user_id:
        raise HTTPException(status_code=403, detail="Only comment owner can update this comment")

    content = normalize_content(payload.content)
    if not content:
        raise HTTPException(status_code=422, detail="Comment content cannot be empty")

    row = update_comment_content(str(comment_id), content)
    send_notification(
        target_user_id=current_user_id,
        notification_type="comment_updated",
        content="Your comment was updated",
        source_id=str(comment_id),
    )

    post_row = get_post_by_id(str(row.get("post_id"))) if row.get("post_id") else None
    if post_row:
        post_owner_id = str(post_row.get("user_id"))
        if post_owner_id != current_user_id:
            send_notification(
                target_user_id=post_owner_id,
                notification_type="post_comment_updated",
                content="A comment on your post was updated",
                source_id=current_user_id,
                actor_id=current_user_id,
            )

    return serialize_comment_rows([row])[0]


@comment_router.delete("/comments/{comment_id}", summary="Delete comment (owner or post owner)")
def delete_comment(
    comment_id: UUID,
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Delete one comment as comment owner or post owner.
    
    Args:
        comment_id (UUID): Comment identifier.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Result of the operation.
    """
    current_user_id = require_current_user(x_user_id, x_access_token)

    comment_row = get_comment_by_id(str(comment_id))
    if not comment_row:
        raise HTTPException(status_code=404, detail="Comment not found")

    comment_owner_id = str(comment_row.get("user_id"))
    is_comment_owner = comment_owner_id == current_user_id

    post_row = get_post_by_id(str(comment_row.get("post_id"))) if comment_row.get("post_id") else None
    post_owner_id = str(post_row.get("user_id")) if post_row and post_row.get("user_id") else None
    is_post_owner = bool(post_owner_id and post_owner_id == current_user_id)

    if not is_comment_owner and not is_post_owner:
        raise HTTPException(status_code=403, detail="Only comment owner or post owner can delete this comment")

    thread_ids = collect_comment_thread_ids(str(comment_id))
    delete_comments_by_ids(thread_ids)

    if is_comment_owner:
        send_notification(
            target_user_id=current_user_id,
            notification_type="comment_deleted",
            content="Your comment was deleted",
            source_id=str(comment_id),
        )
    elif is_post_owner:
        send_notification(
            target_user_id=current_user_id,
            notification_type="post_comment_deleted",
            content="A comment on your post was deleted",
            source_id=str(comment_id),
        )
        if comment_owner_id and comment_owner_id != current_user_id:
            send_notification(
                target_user_id=comment_owner_id,
                notification_type="comment_deleted_by_post_owner",
                content="Your comment was deleted by the post owner",
                source_id=str(comment_id),
                actor_id=current_user_id,
            )

    if post_owner_id and post_owner_id != current_user_id:
        send_notification(
            target_user_id=post_owner_id,
            notification_type="post_comment_deleted",
            content="A comment on your post was deleted",
            source_id=current_user_id,
            actor_id=current_user_id,
        )

    return {"message": "Comment deleted", "comment_id": str(comment_id)}
