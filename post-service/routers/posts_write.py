"""Write endpoints for posts and likes."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException

from core.auth import require_current_user
from schemas.models import PostCreateRequest, PostResponse, PostUpdateRequest
from serializers.post_serializer import serialize_post_rows
from services.notifications import send_notification
from stores.engagement_store import create_post_like, delete_post_like
from stores.post_store import create_post_row, delete_post_with_relations, get_post_by_id, update_post_row
from stores.user_media_store import ensure_media_owned_by_user
from utils.content import normalize_content

post_write_router = APIRouter()


@post_write_router.post("", response_model=PostResponse, status_code=201, summary="Create post")
def create_post(
    payload: PostCreateRequest,
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Create one post for current user.
    
    Args:
        payload (PostCreateRequest): Parsed request payload.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: One post for current user.
    """
    current_user_id = require_current_user(x_user_id, x_access_token)

    content = normalize_content(payload.content)
    media_id = str(payload.media_id) if payload.media_id else None
    if media_id:
        ensure_media_owned_by_user(media_id, current_user_id)

    created_row = create_post_row(current_user_id, content, media_id)
    source_id = str(created_row.get("id")) if created_row.get("id") else None
    send_notification(
        target_user_id=current_user_id,
        notification_type="post_created",
        content="Your post was created",
        source_id=source_id,
    )
    return serialize_post_rows([created_row], current_user_id)[0]


@post_write_router.patch("/{post_id}", response_model=PostResponse, summary="Update my post")
def update_post(
    post_id: UUID,
    payload: PostUpdateRequest,
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Update content/media of one post owned by current user.
    
    Args:
        post_id (UUID): Post identifier.
        payload (PostUpdateRequest): Parsed request payload.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Result of the operation.
    """
    current_user_id = require_current_user(x_user_id, x_access_token)

    post_row = get_post_by_id(str(post_id))
    if not post_row:
        raise HTTPException(status_code=404, detail="Post not found")
    if str(post_row.get("user_id")) != current_user_id:
        raise HTTPException(status_code=403, detail="Only post owner can update this post")

    updates: dict[str, object] = {}
    updated_fields = payload.model_fields_set

    if "content" in updated_fields:
        updates["content"] = normalize_content(payload.content)

    if "media_id" in updated_fields and payload.media_id is not None:
        media_id = str(payload.media_id)
        ensure_media_owned_by_user(media_id, current_user_id)
        updates["media_id"] = media_id

    if payload.clear_media:
        updates["media_id"] = None

    if not updates:
        return serialize_post_rows([post_row], current_user_id)[0]

    final_content = updates["content"] if "content" in updates else normalize_content(post_row.get("content"))
    final_media_id = updates["media_id"] if "media_id" in updates else post_row.get("media_id")
    if not final_content and not final_media_id:
        raise HTTPException(status_code=422, detail="Post must include content or media_id")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    row = update_post_row(str(post_id), updates)

    send_notification(
        target_user_id=current_user_id,
        notification_type="post_updated",
        content="Your post was updated",
        source_id=str(post_id),
    )
    return serialize_post_rows([row], current_user_id)[0]


@post_write_router.delete("/{post_id}", summary="Delete my post")
def delete_post(
    post_id: UUID,
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Delete one post owned by current user.
    
    Args:
        post_id (UUID): Post identifier.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Result of the operation.
    """
    current_user_id = require_current_user(x_user_id, x_access_token)

    post_row = get_post_by_id(str(post_id))
    if not post_row:
        raise HTTPException(status_code=404, detail="Post not found")
    if str(post_row.get("user_id")) != current_user_id:
        raise HTTPException(status_code=403, detail="Only post owner can delete this post")

    delete_post_with_relations(str(post_id))
    send_notification(
        target_user_id=current_user_id,
        notification_type="post_deleted",
        content="Your post was deleted",
        source_id=str(post_id),
    )
    return {"message": "Post deleted", "post_id": str(post_id)}


@post_write_router.post("/{post_id}/like", summary="Like post")
def like_post(
    post_id: UUID,
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Like one post as current user.
    
    Args:
        post_id (UUID): Post identifier.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Result of the operation.
    """
    current_user_id = require_current_user(x_user_id, x_access_token)

    post_row = get_post_by_id(str(post_id))
    if not post_row:
        raise HTTPException(status_code=404, detail="Post not found")

    liked_now = create_post_like(str(post_id), current_user_id)
    if not liked_now:
        return {"message": "Post already liked", "post_id": str(post_id), "liked": True}

    send_notification(
        target_user_id=current_user_id,
        notification_type="post_like_created",
        content="You liked a post",
        source_id=str(post_id),
    )
    post_owner_id = str(post_row.get("user_id"))
    if post_owner_id != current_user_id:
        send_notification(
            target_user_id=post_owner_id,
            notification_type="post_like",
            content="Someone liked your post",
            # Keep actor id in source_id for backward compatibility when
            # notifications.actor_id column is not yet migrated.
            source_id=current_user_id,
            actor_id=current_user_id,
        )
    return {"message": "Post liked", "post_id": str(post_id), "liked": True}


@post_write_router.delete("/{post_id}/like", summary="Unlike post")
def unlike_post(
    post_id: UUID,
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Remove current user's like from one post.
    
    Args:
        post_id (UUID): Post identifier.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Result of the operation.
    """
    current_user_id = require_current_user(x_user_id, x_access_token)

    if not get_post_by_id(str(post_id)):
        raise HTTPException(status_code=404, detail="Post not found")

    delete_post_like(str(post_id), current_user_id)
    send_notification(
        target_user_id=current_user_id,
        notification_type="post_like_deleted",
        content="You unliked a post",
        source_id=str(post_id),
    )
    return {"message": "Post unliked", "post_id": str(post_id), "liked": False}
