"""Post response serialization helpers."""

from schemas.models import PostResponse
from stores.engagement_store import get_post_like_and_comment_stats
from stores.user_media_store import get_avatar_url_map, get_media_url_map, get_users_map


def to_post_response(
    post_row: dict,
    users_map: dict[str, dict],
    avatar_url_map: dict[str, str],
    media_url_map: dict[str, str],
    like_count_map: dict[str, int],
    comment_count_map: dict[str, int],
    liked_post_ids: set[str],
) -> PostResponse:
    """Convert one post row to API response model.
    
    Args:
        post_row (dict): Parameter post_row.
        users_map (dict[str, dict]): Parameter users_map.
        avatar_url_map (dict[str, str]): Parameter avatar_url_map.
        media_url_map (dict[str, str]): Parameter media_url_map.
        like_count_map (dict[str, int]): Parameter like_count_map.
        comment_count_map (dict[str, int]): Parameter comment_count_map.
        liked_post_ids (set[str]): Identifiers for liked post.
    
    Returns:
        PostResponse: One post row to API response model.
    """
    post_id = str(post_row.get("id"))
    author_id = str(post_row.get("user_id"))
    author = users_map.get(author_id, {})
    avatar_id = author.get("avatar_id")
    direct_avatar_url = author.get("avatar_url")
    media_id = post_row.get("media_id")

    return PostResponse(
        id=post_row.get("id"),
        user_id=post_row.get("user_id"),
        content=post_row.get("content"),
        media_id=media_id,
        media_url=media_url_map.get(str(media_id)) if media_id else None,
        created_at=post_row.get("created_at"),
        updated_at=post_row.get("updated_at"),
        like_count=like_count_map.get(post_id, 0),
        comment_count=comment_count_map.get(post_id, 0),
        liked_by_me=post_id in liked_post_ids,
        author_pseudo=author.get("pseudo"),
        author_avatar_id=avatar_id,
        author_avatar_url=(avatar_url_map.get(str(avatar_id)) if avatar_id else None) or direct_avatar_url,
    )


def serialize_post_rows(post_rows: list[dict], current_user_id: str) -> list[PostResponse]:
    """Serialize post rows with author/media and engagement projections.
    
    Args:
        post_rows (list[dict]): Parameter post_rows.
        current_user_id (str): Identifier for current user.
    
    Returns:
        list[PostResponse]: Post rows with author/media and engagement projections.
    """
    if not post_rows:
        return []

    post_ids = [str(row.get("id")) for row in post_rows if row.get("id")]
    author_ids = [str(row.get("user_id")) for row in post_rows if row.get("user_id")]
    media_ids = [str(row.get("media_id")) for row in post_rows if row.get("media_id")]

    users_map = get_users_map(author_ids)
    avatar_ids = [str(user.get("avatar_id")) for user in users_map.values() if user.get("avatar_id")]
    avatar_url_map = get_avatar_url_map(avatar_ids)
    media_url_map = get_media_url_map(media_ids)
    like_count_map, comment_count_map, liked_post_ids = get_post_like_and_comment_stats(post_ids, current_user_id)

    return [
        to_post_response(
            row,
            users_map=users_map,
            avatar_url_map=avatar_url_map,
            media_url_map=media_url_map,
            like_count_map=like_count_map,
            comment_count_map=comment_count_map,
            liked_post_ids=liked_post_ids,
        )
        for row in post_rows
    ]
