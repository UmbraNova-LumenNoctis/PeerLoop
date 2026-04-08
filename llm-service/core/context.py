"""Shared configuration and clients for llm service."""

import logging
import os

from supabase import create_client
from supabase.lib.client_options import ClientOptions

logger = logging.getLogger("llm-service")


def normalize_gemini_api_key(raw_value: str | None) -> str:
    """Normalize API key by removing accidental placeholder suffixes.
    
    Args:
        raw_value (str | None): Parameter raw_value.
    
    Returns:
        str: API key by removing accidental placeholder suffixes.
    """
    key = (raw_value or "").strip()
    if not key:
        return ""

    marker = "REPLACE_ME_"
    if key.startswith("AIza") and marker in key:
        normalized = key.split(marker, 1)[0].rstrip("_-")
        if len(normalized) >= 35:
            logger.warning("Normalized GEMINI_API_KEY by stripping placeholder suffix")
            return normalized
    return key


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GEMINI_API_KEY = normalize_gemini_api_key(os.getenv("GEMINI_API_KEY", ""))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "")
GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_OUTPUT_TOKENS = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "512"))
LLM_SYSTEM_PROMPT = os.getenv("LLM_SYSTEM_PROMPT", "")
LLM_PROVIDER_RETRIES = max(0, int(os.getenv("LLM_PROVIDER_RETRIES", "2")))
LLM_PROVIDER_RETRY_BACKOFF_SECONDS = max(0.1, float(os.getenv("LLM_PROVIDER_RETRY_BACKOFF_SECONDS", "0.6")))
LLM_DEGRADED_FALLBACK_ENABLED = (
    (os.getenv("LLM_DEGRADED_FALLBACK_ENABLED") or "true").strip().lower()
    in {"1", "true", "yes", "on"}
)
SERVICE_NAME = "llm-service"
LLM_MESSAGES_TABLE = "llm_messages"


def new_supabase_client():
    """Create a non-persistent Supabase admin client.
    
    Returns:
        Any: Non-persistent Supabase admin client.
    """
    return create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
        options=ClientOptions(auto_refresh_token=False, persist_session=False),
    )


supabase_admin = new_supabase_client() if SUPABASE_URL and SUPABASE_KEY else None
