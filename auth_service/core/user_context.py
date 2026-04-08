"""Shared context for user router modules."""

import os

from supabase import create_client
from supabase.lib.client_options import ClientOptions

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
PROFILE_SELECT_COLUMNS = "id,pseudo,email,address,bio,avatar_id,avatar_url,cover_id,cover_url,created_at,updated_at"

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY,
    options=ClientOptions(auto_refresh_token=False, persist_session=False),
)
