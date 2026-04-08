"""Shared runtime context and Supabase access for chat service."""

import logging
import os
from threading import Lock

from fastapi import HTTPException
from supabase import create_client
from supabase.lib.client_options import ClientOptions

from shared_schemas.vault_client import PATHS_CHAT_SERVICE, load_vault_secrets

load_vault_secrets(PATHS_CHAT_SERVICE)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL")
INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "")
INTERNAL_TLS_VERIFY = (os.getenv("INTERNAL_TLS_VERIFY") or "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
NOTIFICATION_TIMEOUT_SECONDS = 5.0
SERVICE_NAME = "chat-service"
logger = logging.getLogger("chat-service")


def new_supabase_client():
    """Create a non-persistent Supabase client.
    
    Returns:
        Any: Non-persistent Supabase client.
    """
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY"),
        options=ClientOptions(auto_refresh_token=False, persist_session=False),
    )


supabase_admin = new_supabase_client() if SUPABASE_URL and SUPABASE_KEY else None
supabase_lock = Lock()


def require_supabase():
    """Return ready Supabase client or raise configuration error.
    
    Returns:
        Any: Ready Supabase client or raise configuration error.
    """
    global supabase_admin

    if supabase_admin is not None:
        return supabase_admin

    with supabase_lock:
        if supabase_admin is not None:
            return supabase_admin

        load_vault_secrets(PATHS_CHAT_SERVICE)
        if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
            raise HTTPException(
                status_code=503,
                detail="Chat service is not configured (SUPABASE_URL/SUPABASE_KEY missing)",
            )

        try:
            supabase_admin = new_supabase_client()
            return supabase_admin
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Chat service Supabase client initialization failed: {exc}",
            ) from exc
