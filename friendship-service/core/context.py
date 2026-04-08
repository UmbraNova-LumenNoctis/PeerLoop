"""Shared runtime context and Supabase access for friendship service."""

import logging
import os
from threading import Lock

from fastapi import HTTPException
from supabase import create_client
from supabase.lib.client_options import ClientOptions

from shared_schemas.vault_client import PATHS_FRIENDSHIP_SERVICE, load_vault_secrets

load_vault_secrets(PATHS_FRIENDSHIP_SERVICE)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL")
CHAT_SERVICE_URL = os.getenv("CHAT_SERVICE_URL")
INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN")
INTERNAL_TLS_VERIFY = (os.getenv("INTERNAL_TLS_VERIFY") or "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
NOTIFICATION_TIMEOUT_SECONDS = 5.0

STATUS_PENDING = "pending"
STATUS_ACCEPTED = "accepted"
STATUS_BLOCKED = "blocked"
VALID_STATUSES = {STATUS_PENDING, STATUS_ACCEPTED, STATUS_BLOCKED}
VALID_DIRECTIONS = {"incoming", "outgoing"}

SERVICE_NAME = "friendship-service"
logger = logging.getLogger(SERVICE_NAME)


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
    """Return initialized Supabase client or raise a configuration error.
    
    Returns:
        Any: Initialized Supabase client or raise a configuration error.
    """
    global supabase_admin

    if supabase_admin is not None:
        return supabase_admin

    with supabase_lock:
        if supabase_admin is not None:
            return supabase_admin

        load_vault_secrets(PATHS_FRIENDSHIP_SERVICE)
        if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
            raise HTTPException(
                status_code=503,
                detail="Friendship service is not configured (SUPABASE_URL/SUPABASE_KEY missing)",
            )

        try:
            supabase_admin = new_supabase_client()
            return supabase_admin
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Friendship service Supabase initialization failed: {exc}",
            ) from exc
