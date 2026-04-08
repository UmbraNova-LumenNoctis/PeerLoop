"""Feed filtering and sorting helpers for post listing endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from postgrest.exceptions import APIError

from core.context import SORT_CREATED_AT, SORT_POPULARITY, SORT_UPDATED_AT, require_supabase
from stores.engagement_store import get_post_like_and_comment_stats
from stores.friendship_store import get_accepted_friend_user_ids


def validate_feed_filters(
    user_id: UUID | None,
    friend_only: bool,
    created_before: datetime | None,
    created_after: datetime | None,
) -> None:
    """Validate incompatible feed filters and invalid date window.
    
    Args:
        user_id (UUID | None): User identifier.
        friend_only (bool): Parameter friend_only.
        created_before (datetime | None): Parameter created_before.
        created_after (datetime | None): Parameter created_after.
    
    Returns:
        None: None.
    """
    if user_id is not None and friend_only:
        raise HTTPException(status_code=422, detail="Cannot combine user_id and friend_only filters")

    if created_before is not None and created_after is not None and created_after >= created_before:
        raise HTTPException(status_code=422, detail="created_after must be earlier than created_before")


def build_author_scope(
    current_user_id: str,
    user_id: str | None,
    friend_only: bool,
    include_self: bool,
) -> set[str] | None:
    """Build user id scope for post query filtering.
    
    Args:
        current_user_id (str): Identifier for current user.
        user_id (str | None): User identifier.
        friend_only (bool): Parameter friend_only.
        include_self (bool): Flag controlling whether to self.
    
    Returns:
        set[str] | None: User id scope for post query filtering.
    """
    if user_id:
        return {user_id}

    if not friend_only:
        return None

    friend_ids = get_accepted_friend_user_ids(current_user_id)
    if include_self:
        friend_ids.add(current_user_id)
    return friend_ids


def build_posts_query(author_scope: set[str] | None, created_before: datetime | None, created_after: datetime | None):
    """Build Supabase posts query with optional author and date filters.
    
    Args:
        author_scope (set[str] | None): Parameter author_scope.
        created_before (datetime | None): Parameter created_before.
        created_after (datetime | None): Parameter created_after.
    
    Returns:
        Any: Supabase posts query with optional author and date filters.
    """
    query = require_supabase().table("posts").select("*")
    if author_scope is not None:
        if not author_scope:
            return None
        query = query.in_("user_id", sorted(author_scope))

    if created_before is not None:
        query = query.lt("created_at", created_before.isoformat())
    if created_after is not None:
        query = query.gt("created_at", created_after.isoformat())
    return query


def popularity_sort_key(
    row: dict,
    like_count_map: dict[str, int],
    comment_count_map: dict[str, int],
) -> tuple[int, int, int, str]:
    """Return sortable tuple for popularity feed ordering.
    
    Args:
        row (dict): Parameter row.
        like_count_map (dict[str, int]): Parameter like_count_map.
        comment_count_map (dict[str, int]): Parameter comment_count_map.
    
    Returns:
        tuple[int, int, int, str]: Sortable tuple for popularity feed ordering.
    """
    post_id = str(row.get("id"))
    like_count = like_count_map.get(post_id, 0)
    comment_count = comment_count_map.get(post_id, 0)
    engagement = like_count + comment_count
    created_at = row.get("created_at") or ""
    return engagement, like_count, comment_count, created_at


def load_posts_rows(
    current_user_id: str,
    user_id: str | None,
    friend_only: bool,
    include_self: bool,
    sort_by: str,
    order: str,
    limit: int,
    offset: int,
    created_before: datetime | None,
    created_after: datetime | None,
) -> tuple[list[dict], bool]:
    """Load post rows and has_more flag with DB sorting or popularity sorting.
    
    Args:
        current_user_id (str): Identifier for current user.
        user_id (str | None): User identifier.
        friend_only (bool): Parameter friend_only.
        include_self (bool): Flag controlling whether to self.
        sort_by (str): Parameter sort_by.
        order (str): Parameter order.
        limit (int): Maximum number of items to return.
        offset (int): Pagination offset.
        created_before (datetime | None): Parameter created_before.
        created_after (datetime | None): Parameter created_after.
    
    Returns:
        tuple[list[dict], bool]: Retrieved value.
    """
    author_scope = build_author_scope(current_user_id, user_id, friend_only, include_self)
    sort_desc = order != "asc"

    if sort_by in {SORT_CREATED_AT, SORT_UPDATED_AT}:
        try:
            query = build_posts_query(author_scope, created_before, created_after)
            if query is None:
                return [], False
            result = query.order(sort_by, desc=sort_desc).range(offset, offset + limit).execute()
        except APIError as exc:
            raise HTTPException(status_code=502, detail=f"Post list failed: {exc}") from exc

        rows = result.data or []
        has_more = len(rows) > limit
        return rows[:limit], has_more

    popularity_window_cap = 3000
    chunk_size = 500
    required_rows = offset + limit + 1
    fetched_rows: list[dict] = []
    start = 0

    while len(fetched_rows) < required_rows and start < popularity_window_cap:
        end = min(start + chunk_size - 1, popularity_window_cap - 1)
        try:
            query = build_posts_query(author_scope, created_before, created_after)
            if query is None:
                return [], False
            chunk = query.order("created_at", desc=True).range(start, end).execute().data or []
        except APIError as exc:
            raise HTTPException(status_code=502, detail=f"Post list failed: {exc}") from exc

        if not chunk:
            break

        fetched_rows.extend(chunk)
        if len(chunk) < (end - start + 1):
            break
        start = end + 1

    if not fetched_rows:
        return [], False

    post_ids = [str(row.get("id")) for row in fetched_rows if row.get("id")]
    like_count_map, comment_count_map, _ = get_post_like_and_comment_stats(post_ids, current_user_id)

    fetched_rows.sort(
        key=lambda row: popularity_sort_key(row, like_count_map, comment_count_map),
        reverse=sort_desc,
    )
    has_more = len(fetched_rows) > offset + limit
    return fetched_rows[offset : offset + limit], has_more
