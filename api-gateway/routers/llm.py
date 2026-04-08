"""LLM routes proxied through API gateway."""

from fastapi import APIRouter, Body, Depends, Query, Request
from fastapi.responses import Response

from routers.auth import LLM_SERVICE_URL, proxy_request
from routers.security import require_bearer_token
from shared_schemas.models import LLMPromptRequest

llm_router = APIRouter(prefix="/api/llm", tags=["LLM"])


@llm_router.post(
    "/chat",
    summary="LLM chat completion",
    description="Generate a response with Gemini (default model: gemini-2.5-flash-lite).",
)
async def llm_chat(
    request: Request,
    payload: LLMPromptRequest = Body(...),
    _: str = Depends(require_bearer_token),
) -> Response:
    """Send one prompt to LLM service and return generated response.
    
    Args:
        request (Request): Incoming FastAPI request context.
        payload (LLMPromptRequest): Parsed request payload.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Response: Result of the operation.
    """
    prompt = payload.prompt.strip()
    return await proxy_request(
        method="POST",
        path="llm/chat",
        json_body={"prompt": prompt},
        headers=request.headers,
        params=request.query_params,
        base_url=LLM_SERVICE_URL,
    )


@llm_router.get(
    "/history",
    summary="LLM chat history",
    description="List persisted LLM messages for the authenticated user.",
)
async def llm_history(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: str = Depends(require_bearer_token),
) -> Response:
    """List paginated LLM message history for the current user.
    
    Args:
        request (Request): Incoming FastAPI request context.
        limit (int): Maximum number of items to return.
        offset (int): Pagination offset.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Response: Paginated LLM message history for the current user.
    """
    params = dict(request.query_params)
    params["limit"] = str(limit)
    params["offset"] = str(offset)

    return await proxy_request(
        method="GET",
        path="llm/history",
        headers=request.headers,
        params=params,
        base_url=LLM_SERVICE_URL,
    )


@llm_router.delete(
    "/history",
    summary="Delete LLM chat history",
    description="Delete all persisted LLM messages for the authenticated user.",
)
async def llm_history_delete(
    request: Request,
    _: str = Depends(require_bearer_token),
) -> Response:
    """Delete all stored LLM messages for the current user.
    
    Args:
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Response: Result of the operation.
    """
    return await proxy_request(
        method="DELETE",
        path="llm/history",
        headers=request.headers,
        params=request.query_params,
        base_url=LLM_SERVICE_URL,
    )
