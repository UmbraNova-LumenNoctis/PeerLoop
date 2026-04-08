"""Comment response serialization helpers."""

from schemas.models import CommentResponse
from stores.user_media_store import get_avatar_url_map, get_users_map


def to_comment_response(comment_row: dict, users_map: dict[str, dict], avatar_url_map: dict[str, str]) -> CommentResponse:
    """Convert one comment row to API response model.
    
    Args:
        comment_row (dict): Parameter comment_row.
        users_map (dict[str, dict]): Parameter users_map.
        avatar_url_map (dict[str, str]): Parameter avatar_url_map.
    
    Returns:
        CommentResponse: One comment row to API response model.
    """
    author_id = str(comment_row.get("user_id"))
    author = users_map.get(author_id, {})
    avatar_id = author.get("avatar_id")
    direct_avatar_url = author.get("avatar_url")

    return CommentResponse(
        id=comment_row.get("id"),
        post_id=comment_row.get("post_id"),
        user_id=comment_row.get("user_id"),
        parent_comment_id=comment_row.get("parent_comment_id"),
        content=comment_row.get("content"),
        created_at=comment_row.get("created_at"),
        author_pseudo=author.get("pseudo"),
        author_avatar_id=avatar_id,
        author_avatar_url=(avatar_url_map.get(str(avatar_id)) if avatar_id else None) or direct_avatar_url,
    )


def serialize_comment_rows(comment_rows: list[dict]) -> list[CommentResponse]:
    """Serialize comment rows with author projection.
    
    Args:
        comment_rows (list[dict]): Parameter comment_rows.
    
    Returns:
        list[CommentResponse]: Comment rows with author projection.
    """
    if not comment_rows:
        return []

    author_ids = [str(row.get("user_id")) for row in comment_rows if row.get("user_id")]
    users_map = get_users_map(author_ids)
    avatar_ids = [str(user.get("avatar_id")) for user in users_map.values() if user.get("avatar_id")]
    avatar_url_map = get_avatar_url_map(avatar_ids)

    return [to_comment_response(row, users_map=users_map, avatar_url_map=avatar_url_map) for row in comment_rows]
