"""Post search workflow for search-service."""

from fastapi import HTTPException
from postgrest.exceptions import APIError

from ..core.context import require_supabase
from ..stores.projection_store import get_avatar_url_map, get_media_url_map, get_post_stats, get_users_map
from .ranking import score_post_row
from .user_search import search_users_raw


def fetch_posts_by_content(pattern: str, candidate_limit: int) -> list[dict]:
    """Fetch posts whose content matches the search pattern.
    
    Args:
        pattern (str): Parameter pattern.
        candidate_limit (int): Parameter candidate_limit.
    
    Returns:
        list[dict]: Posts whose content matches the search pattern.
    """
    try:
        result = (
            require_supabase()
            .table("posts")
            .select("id,user_id,content,media_id,created_at,updated_at")
            .ilike("content", pattern)
            .order("created_at", desc=True)
            .limit(candidate_limit)
            .execute()
        )
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Post search failed: {exc}") from exc

    return result.data or []


def fetch_posts_by_authors(user_ids: list[str], candidate_limit: int) -> list[dict]:
    """Fetch recent posts authored by matching users.
    
    Args:
        user_ids (list[str]): Identifiers for user.
        candidate_limit (int): Parameter candidate_limit.
    
    Returns:
        list[dict]: Recent posts authored by matching users.
    """
    if not user_ids:
        return []

    try:
        result = (
            require_supabase()
            .table("posts")
            .select("id,user_id,content,media_id,created_at,updated_at")
            .in_("user_id", user_ids)
            .order("created_at", desc=True)
            .limit(candidate_limit)
            .execute()
        )
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Post search failed: {exc}") from exc

    return result.data or []


def rank_post_rows(query: str, rows: list[dict], users_map: dict[str, dict]) -> list[tuple[float, dict]]:
    """Rank candidate posts by fuzzy relevance and recency boost.
    
    Args:
        query (str): Search query string.
        rows (list[dict]): Parameter rows.
        users_map (dict[str, dict]): Parameter users_map.
    
    Returns:
        list[tuple[float, dict]]: Result of the operation.
    """
    scored_rows: list[tuple[float, dict]] = []
    for row in rows:
        author_id = str(row.get("user_id"))
        score = score_post_row(query, row, users_map.get(author_id))
        if score > 0.05:
            scored_rows.append((score, row))

    scored_rows.sort(
        key=lambda item: (
            item[0],
            str(item[1].get("created_at") or ""),
        ),
        reverse=True,
    )
    return scored_rows


def serialize_posts(
    paged_rows: list[dict],
    current_user_id: str,
    default_avatar_url: str | None,
) -> list[dict]:
    """Serialize post rows into API payload with media and engagement projection.
    
    Args:
        paged_rows (list[dict]): Parameter paged_rows.
        current_user_id (str): Identifier for current user.
        default_avatar_url (str | None): URL for default avatar.
    
    Returns:
        list[dict]: Post rows into API payload with media and engagement projection.
    """
    post_ids = [str(row.get("id")) for row in paged_rows if row.get("id")]
    user_ids = [str(row.get("user_id")) for row in paged_rows if row.get("user_id")]
    media_ids = [str(row.get("media_id")) for row in paged_rows if row.get("media_id")]

    users_map = get_users_map(user_ids)
    avatar_ids = [str(user.get("avatar_id")) for user in users_map.values() if user.get("avatar_id")]
    avatar_urls = get_avatar_url_map(avatar_ids)
    media_urls = get_media_url_map(media_ids)
    like_count_map, comment_count_map, liked_post_ids = get_post_stats(post_ids, current_user_id)

    items: list[dict] = []
    for row in paged_rows:
        row_id = str(row.get("id"))
        author_id = str(row.get("user_id"))
        author = users_map.get(author_id, {})
        author_avatar_id = author.get("avatar_id")

        items.append(
            {
                "id": row.get("id"),
                "user_id": row.get("user_id"),
                "content": row.get("content"),
                "media_id": row.get("media_id"),
                "media_url": media_urls.get(str(row.get("media_id"))) if row.get("media_id") else None,
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at"),
                "author_pseudo": author.get("pseudo"),
                "author_avatar_url": (
                    avatar_urls.get(str(author_avatar_id)) if author_avatar_id else default_avatar_url
                ),
                "like_count": like_count_map.get(row_id, 0),
                "comment_count": comment_count_map.get(row_id, 0),
                "liked_by_me": row_id in liked_post_ids,
            }
        )

    return items


def search_posts_raw(
    query: str,
    limit: int,
    offset: int,
    current_user_id: str,
    default_avatar_url: str | None,
) -> tuple[list[dict], int]:
    """Search posts by content and matching author profiles.
    
    Args:
        query (str): Search query string.
        limit (int): Maximum number of items to return.
        offset (int): Pagination offset.
        current_user_id (str): Identifier for current user.
        default_avatar_url (str | None): URL for default avatar.
    
    Returns:
        tuple[list[dict], int]: Result of the operation.
    """
    term = query.strip()
    if not term:
        return [], 0

    pattern = f"%{term}%"
    candidate_limit = min(500, max(limit + offset + 160, 220))

    candidate_posts: dict[str, dict] = {}
    for row in fetch_posts_by_content(pattern, candidate_limit):
        row_id = str(row.get("id"))
        if row_id:
            candidate_posts[row_id] = row

    matched_users = search_users_raw(term, limit=80, default_avatar_url=default_avatar_url)
    matched_user_ids = [str(row["id"]) for row in matched_users if row.get("id")]
    for row in fetch_posts_by_authors(matched_user_ids, candidate_limit):
        row_id = str(row.get("id"))
        if row_id:
            candidate_posts[row_id] = row

    if not candidate_posts:
        return [], 0

    all_rows = list(candidate_posts.values())
    all_author_ids = [str(row.get("user_id")) for row in all_rows if row.get("user_id")]
    ranked = rank_post_rows(term, all_rows, get_users_map(all_author_ids))

    total = len(ranked)
    paged_rows = [row for _, row in ranked][offset : offset + limit]
    items = serialize_posts(paged_rows, current_user_id, default_avatar_url)
    return items, total
