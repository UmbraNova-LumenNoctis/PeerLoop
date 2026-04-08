"""Shared runtime context and Supabase client management for notification service."""

import os
from threading import Lock

from fastapi import HTTPException
from supabase import create_client
from supabase.lib.client_options import ClientOptions

from shared_schemas.vault_client import PATHS_NOTIFICATION_SERVICE, load_vault_secrets

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN")
NOTIFICATIONS_TABLE = "notifications"
SERVICE_NAME = "notification-service"


def new_supabase_client():
    """Create a non-persistent Supabase admin client.
    
    Returns:
        Any: Non-persistent Supabase admin client.
    """
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY"),
        options=ClientOptions(auto_refresh_token=False, persist_session=False),
    )


supabase_admin = new_supabase_client() if SUPABASE_URL and SUPABASE_KEY else None
supabase_lock = Lock()


def require_supabase():
    """Return initialized Supabase client or raise a service configuration error.
    
    Returns:
        Any: Initialized Supabase client or raise a service configuration error.
    """
    global supabase_admin

    if supabase_admin is not None:
        return supabase_admin

    with supabase_lock:
        if supabase_admin is not None:
            return supabase_admin

        load_vault_secrets(PATHS_NOTIFICATION_SERVICE)
        if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
            raise HTTPException(
                status_code=503,
                detail="Notification service is not configured (SUPABASE_URL/SUPABASE_KEY missing)",
            )

        try:
            supabase_admin = new_supabase_client()
            return supabase_admin
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Notification service Supabase client initialization failed: {exc}",
            ) from exc
