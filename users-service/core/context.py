"""Shared runtime context for users service."""

import logging
import os

from supabase import create_client
from supabase.lib.client_options import ClientOptions

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL")
INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN")
INTERNAL_TLS_VERIFY = (os.getenv("INTERNAL_TLS_VERIFY") or "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
NOTIFICATION_TIMEOUT_SECONDS = 5.0
DEFAULT_AVATAR_URL = os.getenv("DEFAULT_AVATAR_URL")
DEFAULT_COVER_URL = (os.getenv("DEFAULT_COVER_URL") or "").strip() or None
SERVICE_NAME = "users-service"
logger = logging.getLogger("users-service")


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


supabase_admin = new_supabase_client()
