"""LLM history persistence helpers."""

from fastapi import HTTPException
from postgrest.exceptions import APIError

from core.context import LLM_MESSAGES_TABLE, logger, supabase_admin
from schemas.models import LLMHistoryItem


def insert_llm_message(
    user_id: str,
    role: str,
    content: str,
    provider: str | None = None,
    model: str | None = None,
    finish_reason: str | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
) -> dict:
    """Persist one LLM message row.
    
    Args:
        user_id (str): User identifier.
        role (str): Parameter role.
        content (str): Text content.
        provider (str | None): Provider identifier.
        model (str | None): Model name.
        finish_reason (str | None): Parameter finish_reason.
        prompt_tokens (int | None): Parameter prompt_tokens.
        completion_tokens (int | None): Parameter completion_tokens.
        total_tokens (int | None): Parameter total_tokens.
    
    Returns:
        dict: Result of the operation.
    """
    if not supabase_admin:
        raise HTTPException(status_code=503, detail="Supabase is not configured")

    payload = {
        "user_id": user_id,
        "role": role,
        "content": content,
        "provider": provider,
        "model": model,
        "finish_reason": finish_reason,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }
    try:
        created = supabase_admin.table(LLM_MESSAGES_TABLE).insert(payload).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"LLM message persistence failed: {exc}") from exc

    rows = created.data or []
    if not rows:
        raise HTTPException(status_code=502, detail="LLM message was created but not returned")
    return rows[0]


def try_insert_llm_message(**kwargs) -> None:
    """Best-effort history insert that never breaks chat flow.
    
    Args:
        **kwargs (Any): Additional keyword arguments.
    
    Returns:
        None: None.
    """
    try:
        insert_llm_message(**kwargs)
    except HTTPException as exc:
        logger.warning("Skipping LLM history persistence: %s", exc.detail)
    except Exception as exc:
        logger.warning("Unexpected LLM history persistence failure: %s", exc)


def serialize_history_rows(rows: list[dict]) -> list[LLMHistoryItem]:
    """Convert LLM DB rows into API response history models.
    
    Args:
        rows (list[dict]): Parameter rows.
    
    Returns:
        list[LLMHistoryItem]: LLM DB rows into API response history models.
    """
    history: list[LLMHistoryItem] = []
    for row in rows:
        role = str(row.get("role") or "")
        if role not in {"user", "assistant"}:
            continue

        history.append(
            LLMHistoryItem(
                id=row.get("id"),
                role=role,
                content=row.get("content") or "",
                provider=row.get("provider"),
                model=row.get("model"),
                finish_reason=row.get("finish_reason"),
                prompt_tokens=row.get("prompt_tokens"),
                completion_tokens=row.get("completion_tokens"),
                total_tokens=row.get("total_tokens"),
                created_at=row.get("created_at"),
            )
        )
    return history


def fetch_history_rows(current_user_id: str, limit: int, offset: int) -> list[dict]:
    """Fetch paginated history rows for one user.
    
    Args:
        current_user_id (str): Identifier for current user.
        limit (int): Maximum number of items to return.
        offset (int): Pagination offset.
    
    Returns:
        list[dict]: Paginated history rows for one user.
    """
    if not supabase_admin:
        return []

    try:
        result = (
            supabase_admin.table(LLM_MESSAGES_TABLE)
            .select("*")
            .eq("user_id", current_user_id)
            .order("created_at", desc=False)
            .range(offset, offset + limit - 1)
            .execute()
        )
    except APIError as exc:
        detail = str(exc).lower()
        if "llm_messages" in detail and ("does not exist" in detail or "not found" in detail):
            logger.warning("LLM history table missing; returning empty history")
            return []
        raise HTTPException(status_code=502, detail=f"LLM history lookup failed: {exc}") from exc

    return result.data or []


def delete_history_rows(current_user_id: str) -> int:
    """Delete all history rows for one user and return affected count.
    
    Args:
        current_user_id (str): Identifier for current user.
    
    Returns:
        int: Result of the operation.
    """
    if not supabase_admin:
        return 0

    try:
        existing_rows = (
            supabase_admin.table(LLM_MESSAGES_TABLE)
            .select("id")
            .eq("user_id", current_user_id)
            .execute()
            .data
            or []
        )
    except APIError as exc:
        detail = str(exc).lower()
        if "llm_messages" in detail and ("does not exist" in detail or "not found" in detail):
            logger.warning("LLM history table missing; nothing to delete")
            return 0
        raise HTTPException(status_code=502, detail=f"LLM history lookup failed: {exc}") from exc

    deleted_count = len(existing_rows)
    if not deleted_count:
        return 0

    try:
        supabase_admin.table(LLM_MESSAGES_TABLE).delete().eq("user_id", current_user_id).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"LLM history deletion failed: {exc}") from exc
    return deleted_count
