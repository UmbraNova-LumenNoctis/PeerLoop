"""Ranking functions for user and post search results."""

from datetime import datetime, timezone

from .scoring import fuzzy_similarity, normalize_text


def score_user_row(query: str, row: dict) -> float:
    """Return ranking score for one user row.
    
    Args:
        query (str): Search query string.
        row (dict): Parameter row.
    
    Returns:
        float: Ranking score for one user row.
    """
    pseudo_score = fuzzy_similarity(query, row.get("pseudo"))
    email_score = fuzzy_similarity(query, row.get("email"))
    bio_score = fuzzy_similarity(query, row.get("bio"))

    score = (pseudo_score * 0.62) + (email_score * 0.24) + (bio_score * 0.14)
    if normalize_text(query) == normalize_text(row.get("pseudo")):
        score += 0.08
    return min(score, 1.25)


def recency_boost(created_at: str | None) -> float:
    """Return recency bonus score for post ranking.
    
    Args:
        created_at (str | None): Parameter created_at.
    
    Returns:
        float: Recency bonus score for post ranking.
    """
    if not created_at:
        return 0.0

    try:
        parsed = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
    except Exception:
        return 0.0

    age_hours = max(
        0.0,
        (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds() / 3600.0,
    )
    return 0.08 / (1.0 + (age_hours / 72.0))


def score_post_row(query: str, row: dict, author_row: dict | None) -> float:
    """Return ranking score for one post row.
    
    Args:
        query (str): Search query string.
        row (dict): Parameter row.
        author_row (dict | None): Parameter author_row.
    
    Returns:
        float: Ranking score for one post row.
    """
    content_score = fuzzy_similarity(query, row.get("content"))
    author_pseudo_score = fuzzy_similarity(query, author_row.get("pseudo") if author_row else None)
    author_email_score = fuzzy_similarity(query, author_row.get("email") if author_row else None)
    author_score = max(author_pseudo_score, author_email_score)

    base = (content_score * 0.74) + (author_score * 0.26)
    if row.get("media_id") and author_score > 0:
        base = max(base, author_score * 0.72)

    return min(1.4, base + recency_boost(row.get("created_at")))
