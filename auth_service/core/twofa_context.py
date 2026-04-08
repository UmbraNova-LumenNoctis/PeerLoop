"""Shared context for 2FA router modules."""

import os

from supabase import create_client
from supabase.lib.client_options import ClientOptions

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SECRET_COLUMNS = ("totp_secret", "twofa_secret", "otp_secret")
FLAG_COLUMNS = ("totp_enabled", "twofa_enabled", "is_2fa_enabled")


def new_supabase_client():
    """Create a non-persistent Supabase client for 2FA operations.
    
    Returns:
        Any: Non-persistent Supabase client for 2FA operations.
    """
    return create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
        options=ClientOptions(auto_refresh_token=False, persist_session=False),
    )


supabase_admin = new_supabase_client()
