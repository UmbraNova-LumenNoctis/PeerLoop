"""LLM history routes."""

from fastapi import APIRouter, Header, HTTPException, Query

from core.auth_utils import resolve_user_id
from schemas.models import LLMHistoryDeleteResponse, LLMHistoryItem
from stores.storage import delete_history_rows, fetch_history_rows, serialize_history_rows

llm_history_router = APIRouter()


@llm_history_router.get("/history", response_model=list[LLMHistoryItem], summary="List LLM chat history")
def list_history(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Return paginated LLM history for current user.
    
    Args:
        limit (int): Maximum number of items to return.
        offset (int): Pagination offset.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Paginated LLM history for current user.
    """
    current_user_id = resolve_user_id(x_user_id, x_access_token)
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: missing or invalid access token")

    rows = fetch_history_rows(current_user_id, limit, offset)
    return serialize_history_rows(rows)


@llm_history_router.delete(
    "/history",
    response_model=LLMHistoryDeleteResponse,
    summary="Delete LLM chat history",
)
def delete_history(
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Delete all persisted LLM messages for current user.
    
    Args:
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Result of the operation.
    """
    current_user_id = resolve_user_id(x_user_id, x_access_token)
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: missing or invalid access token")

    deleted_count = delete_history_rows(current_user_id)
    return LLMHistoryDeleteResponse(deleted_count=deleted_count)
