"""Gemini payload and error interpretation helpers."""

import httpx
from fastapi import HTTPException

from core.context import LLM_MAX_OUTPUT_TOKENS, LLM_SYSTEM_PROMPT, LLM_TEMPERATURE


def build_gemini_payload(prompt: str) -> dict:
    """Build Gemini generation payload from user prompt and runtime config.
    
    Args:
        prompt (str): Prompt text.
    
    Returns:
        dict: Gemini generation payload from user prompt and runtime config.
    """
    prompt_text = prompt.strip()
    if not prompt_text:
        raise HTTPException(status_code=422, detail="Prompt cannot be empty")

    request_payload: dict = {
        "contents": [{"role": "user", "parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "temperature": LLM_TEMPERATURE,
            "maxOutputTokens": LLM_MAX_OUTPUT_TOKENS,
        },
    }
    if LLM_SYSTEM_PROMPT.strip():
        request_payload["systemInstruction"] = {"parts": [{"text": LLM_SYSTEM_PROMPT.strip()}]}
    return request_payload


def extract_error_detail(response: httpx.Response) -> str:
    """Extract normalized detail message from Gemini HTTP response.
    
    Args:
        response (httpx.Response): FastAPI response object to mutate.
    
    Returns:
        str: Normalized detail message from Gemini HTTP response.
    """
    try:
        payload = response.json()
        error_obj = payload.get("error")
        if isinstance(error_obj, dict):
            message = error_obj.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()
    except Exception:
        pass

    text = (response.text or "").strip()
    return text[:300] if text else f"HTTP {response.status_code}"


def is_retriable_model_error(status_code: int, detail: str) -> bool:
    """Tell whether error likely indicates unsupported/unknown model.
    
    Args:
        status_code (int): HTTP status code.
        detail (str): Parameter detail.
    
    Returns:
        bool: True if retriable model error, otherwise False.
    """
    if status_code not in (400, 404):
        return False

    normalized = (detail or "").lower()
    markers = ("model", "not found", "unknown model", "does not exist", "unsupported model")
    return any(marker in normalized for marker in markers)


def is_credentials_error(status_code: int, detail: str) -> bool:
    """Tell whether error indicates invalid provider credentials.
    
    Args:
        status_code (int): HTTP status code.
        detail (str): Parameter detail.
    
    Returns:
        bool: True if credentials error, otherwise False.
    """
    if status_code in (401, 403):
        return True
    if status_code != 400:
        return False

    normalized = (detail or "").lower()
    markers = (
        "api key not valid",
        "invalid api key",
        "authentication",
        "unauthorized",
        "permission denied",
        "credentials",
    )
    return any(marker in normalized for marker in markers)


def extract_text_and_usage(payload: dict) -> tuple[str, str | None, dict]:
    """Extract assistant text, finish reason, and token usage from Gemini payload.
    
    Args:
        payload (dict): Parsed request payload.
    
    Returns:
        tuple[str, str | None, dict]: Assistant text, finish reason, and token usage from Gemini
                                      payload.
    """
    candidates = payload.get("candidates") or []
    if not candidates:
        prompt_feedback = payload.get("promptFeedback") or {}
        block_reason = prompt_feedback.get("blockReason")
        if block_reason:
            raise HTTPException(status_code=422, detail=f"Prompt blocked by provider: {block_reason}")
        raise HTTPException(status_code=502, detail="Gemini response has no candidates")

    first_candidate = candidates[0]
    content = first_candidate.get("content") or {}
    parts = content.get("parts") or []
    text = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
    if not text:
        raise HTTPException(status_code=502, detail="Gemini returned an empty response")

    finish_reason = first_candidate.get("finishReason")
    usage = payload.get("usageMetadata") or {}
    return text, finish_reason, usage
