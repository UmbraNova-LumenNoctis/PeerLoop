"""User search workflow for search-service."""

from fastapi import HTTPException
from postgrest.exceptions import APIError

from ..core.context import require_supabase
from ..stores.projection_store import get_avatar_url_map
from .ranking import score_user_row
from .scoring import normalize_text


def fetch_user_candidate_rows(pattern: str, candidate_limit: int) -> list[dict]:
    """Fetch candidate user rows matching pseudo, email or bio.
    
    Args:
        pattern (str): Parameter pattern.
        candidate_limit (int): Parameter candidate_limit.
    
    Returns:
        list[dict]: Candidate user rows matching pseudo, email or bio.
    """
    rows_by_id: dict[str, dict] = {}

    try:
        by_pseudo = (
            require_supabase()
            .table("users")
            .select("id,pseudo,email,bio,avatar_id")
            .ilike("pseudo", pattern)
            .limit(candidate_limit)
            .execute()
        )
        by_email = (
            require_supabase()
            .table("users")
            .select("id,pseudo,email,bio,avatar_id")
            .ilike("email", pattern)
            .limit(candidate_limit)
            .execute()
        )
        by_bio = (
            require_supabase()
            .table("users")
            .select("id,pseudo,email,bio,avatar_id")
            .ilike("bio", pattern)
            .limit(candidate_limit)
            .execute()
        )
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"User search failed: {exc}") from exc

    for query_rows in (by_pseudo.data or [], by_email.data or [], by_bio.data or []):
        for row in query_rows:
            user_id = str(row.get("id"))
            if user_id:
                rows_by_id[user_id] = row

    return list(rows_by_id.values())


def sort_user_rows_by_score(query: str, rows: list[dict]) -> list[dict]:
    """Sort user rows by fuzzy score and deterministic text tie-breakers.
    
    Args:
        query (str): Search query string.
        rows (list[dict]): Parameter rows.
    
    Returns:
        list[dict]: Result of the operation.
    """
    scored_rows: list[tuple[float, dict]] = []
    for row in rows:
        score = score_user_row(query, row)
        if score > 0.06:
            scored_rows.append((score, row))

    scored_rows.sort(
        key=lambda item: (
            -item[0],
            normalize_text(item[1].get("pseudo")),
            normalize_text(item[1].get("email")),
        )
    )
    return [row for _, row in scored_rows]


def serialize_user_rows(rows: list[dict], default_avatar_url: str | None) -> list[dict]:
    """Serialize user rows into API payload structure.
    
    Args:
        rows (list[dict]): Parameter rows.
        default_avatar_url (str | None): URL for default avatar.
    
    Returns:
        list[dict]: User rows into API payload structure.
    """
    avatar_ids = [str(row.get("avatar_id")) for row in rows if row.get("avatar_id")]
    avatar_urls = get_avatar_url_map(avatar_ids)

    return [
        {
            "id": row.get("id"),
            "pseudo": row.get("pseudo"),
            "email": row.get("email"),
            "bio": row.get("bio"),
            "avatar_id": row.get("avatar_id"),
            "avatar_url": (
                avatar_urls.get(str(row.get("avatar_id"))) or default_avatar_url
                if row.get("avatar_id")
                else default_avatar_url
            ),
        }
        for row in rows
    ]


def search_users_raw(query: str, limit: int, default_avatar_url: str | None) -> list[dict]:
    """Search users by pseudo, email and bio with fuzzy ranking.
    
    Args:
        query (str): Search query string.
        limit (int): Maximum number of items to return.
        default_avatar_url (str | None): URL for default avatar.
    
    Returns:
        list[dict]: Result of the operation.
    """
    term = query.strip()
    if not term:
        return []

    pattern = f"%{term}%"
    candidate_limit = min(400, max(limit * 12, 120))
    candidates = fetch_user_candidate_rows(pattern, candidate_limit)
    if not candidates:
        return []

    ranked_rows = sort_user_rows_by_score(term, candidates)[:limit]
    return serialize_user_rows(ranked_rows, default_avatar_url)
