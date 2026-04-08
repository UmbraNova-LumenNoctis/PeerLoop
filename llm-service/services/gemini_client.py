"""Gemini provider client with retries and fallback helpers."""

import asyncio

import httpx
from fastapi import HTTPException

from core.context import (
    GEMINI_API_KEY,
    GEMINI_BASE_URL,
    GEMINI_MODEL,
    LLM_PROVIDER_RETRIES,
    LLM_PROVIDER_RETRY_BACKOFF_SECONDS,
    LLM_TIMEOUT_SECONDS,
    logger,
)
from services.gemini_helpers import extract_error_detail, is_credentials_error, is_retriable_model_error


def candidate_models() -> list[str]:
    """Build ordered list of candidate Gemini models.
    
    Returns:
        list[str]: Ordered list of candidate Gemini models.
    """
    candidates = [
        (GEMINI_MODEL or "").strip(),
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
    ]

    unique_candidates: list[str] = []
    for model in candidates:
        if model and model not in unique_candidates:
            unique_candidates.append(model)
    return unique_candidates


async def request_gemini_with_model_fallback(request_payload: dict) -> tuple[str, dict]:
    """Call Gemini with retries and model fallback strategy.
    
    Args:
        request_payload (dict): Parameter request_payload.
    
    Returns:
        tuple[str, dict]: Result of the operation.
    """
    models = candidate_models()
    if not models:
        raise HTTPException(status_code=422, detail="Model name is required")

    last_detail = "Gemini request failed"
    for model in models:
        endpoint = f"{GEMINI_BASE_URL.rstrip('/')}/models/{model}:generateContent"
        for attempt in range(1, LLM_PROVIDER_RETRIES + 2):
            try:
                async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
                    response = await client.post(
                        endpoint,
                        params={"key": GEMINI_API_KEY},
                        json=request_payload,
                    )
            except httpx.RequestError as exc:
                last_detail = f"Gemini API unreachable: {exc}"
                if attempt <= LLM_PROVIDER_RETRIES:
                    logger.warning(
                        "Gemini network error for model %s (attempt %s/%s): %s",
                        model,
                        attempt,
                        LLM_PROVIDER_RETRIES + 1,
                        exc,
                    )
                    await asyncio.sleep(LLM_PROVIDER_RETRY_BACKOFF_SECONDS * attempt)
                    continue
                break

            if response.status_code == 200:
                try:
                    payload = response.json()
                except Exception as exc:
                    raise HTTPException(status_code=502, detail="Invalid JSON response from Gemini") from exc
                return model, payload

            if response.status_code == 429:
                raise HTTPException(status_code=429, detail="Gemini rate limit exceeded")

            if response.status_code >= 500:
                last_detail = f"Gemini provider error (HTTP {response.status_code})"
                if attempt <= LLM_PROVIDER_RETRIES:
                    logger.warning(
                        "Gemini provider transient error for model %s (attempt %s/%s): %s",
                        model,
                        attempt,
                        LLM_PROVIDER_RETRIES + 1,
                        response.status_code,
                    )
                    await asyncio.sleep(LLM_PROVIDER_RETRY_BACKOFF_SECONDS * attempt)
                    continue
                break

            detail = extract_error_detail(response)
            if is_credentials_error(response.status_code, detail):
                raise HTTPException(status_code=503, detail=f"Gemini credentials/configuration error: {detail}")

            if is_retriable_model_error(response.status_code, detail):
                last_detail = detail
                logger.warning("Gemini model %s failed, trying fallback: %s", model, detail)
                break

            if response.status_code in (400, 422):
                raise HTTPException(status_code=422, detail=f"Gemini rejected the prompt: {detail}")

            logger.warning(
                "Gemini non-success response for model %s (HTTP %s): %s",
                model,
                response.status_code,
                detail,
            )
            raise HTTPException(status_code=502, detail=f"Gemini request failed: {detail}")

    logger.warning("Gemini request failed after model fallback/retries: %s", last_detail)
    raise HTTPException(status_code=502, detail=f"Gemini request failed: {last_detail}")


def build_degraded_fallback_reply(prompt: str, reason: str) -> str:
    """Build deterministic local fallback text when provider is unavailable.
    
    Args:
        prompt (str): Prompt text.
        reason (str): Parameter reason.
    
    Returns:
        str: Deterministic local fallback text when provider is unavailable.
    """
    sanitized_prompt = " ".join((prompt or "").split())
    if len(sanitized_prompt) > 280:
        sanitized_prompt = f"{sanitized_prompt[:280]}..."

    normalized_reason = " ".join((reason or "").split()) or "provider unavailable"
    return (
        "LLM provider is temporarily unavailable. "
        f"Reason: {normalized_reason}. "
        "I kept your request so you can retry shortly. "
        f"Prompt: \"{sanitized_prompt}\""
    )
