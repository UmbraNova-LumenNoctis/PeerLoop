"""LLM chat completion route."""

from fastapi import APIRouter, Header, HTTPException

from core.auth_utils import resolve_user_id
from core.context import GEMINI_API_KEY, GEMINI_MODEL, LLM_DEGRADED_FALLBACK_ENABLED, logger
from services.gemini_client import build_degraded_fallback_reply, request_gemini_with_model_fallback
from services.gemini_helpers import build_gemini_payload, extract_text_and_usage
from schemas.models import LLMChatResponse, LLMPromptRequest
from stores.storage import try_insert_llm_message

llm_chat_router = APIRouter()


@llm_chat_router.post("/chat", response_model=LLMChatResponse, summary="Generate completion with Gemini")
async def chat_completion(
    payload: LLMPromptRequest,
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
):
    """Generate one assistant message from prompt, with degraded fallback support.
    
    Args:
        payload (LLMPromptRequest): Parsed request payload.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Result of the operation.
    """
    current_user_id = resolve_user_id(x_user_id, x_access_token)
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: missing or invalid access token")

    prompt_text = payload.prompt.strip()
    try_insert_llm_message(user_id=current_user_id, role="user", content=prompt_text)

    provider = "google-gemini"
    model = GEMINI_MODEL
    finish_reason: str | None = None
    usage: dict = {}

    try:
        if not GEMINI_API_KEY:
            raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not configured")

        request_payload = build_gemini_payload(prompt_text)
        model, response_payload = await request_gemini_with_model_fallback(request_payload)
        text, finish_reason, usage = extract_text_and_usage(response_payload)
    except HTTPException as exc:
        if not LLM_DEGRADED_FALLBACK_ENABLED or exc.status_code not in {429, 502, 503}:
            raise

        logger.warning("LLM degraded fallback activated: %s", exc.detail)
        provider = "local-fallback"
        model = "local-fallback"
        finish_reason = "provider_unavailable_fallback"
        usage = {}
        text = build_degraded_fallback_reply(prompt_text, str(exc.detail))

    try_insert_llm_message(
        user_id=current_user_id,
        role="assistant",
        content=text,
        provider=provider,
        model=model,
        finish_reason=finish_reason,
        prompt_tokens=usage.get("promptTokenCount"),
        completion_tokens=usage.get("candidatesTokenCount"),
        total_tokens=usage.get("totalTokenCount"),
    )

    return LLMChatResponse(
        provider=provider,
        model=model,
        text=text,
        finish_reason=finish_reason,
        prompt_tokens=usage.get("promptTokenCount"),
        completion_tokens=usage.get("candidatesTokenCount"),
        total_tokens=usage.get("totalTokenCount"),
    )
