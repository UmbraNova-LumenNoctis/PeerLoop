"""Runtime configuration refresh helpers for file service."""

import os

from imagekitio import ImageKit
from supabase import create_client
from supabase.lib.client_options import ClientOptions

from core import context


def is_placeholder_secret(value: str | None) -> bool:
    """Return whether a secret value looks unset or placeholder-like.
    
    Args:
        value (str | None): Parameter value.
    
    Returns:
        bool: True if placeholder secret, otherwise False.
    """
    if value is None:
        return True

    normalized = value.strip()
    if not normalized:
        return True

    lowered = normalized.lower()
    return (
        lowered.startswith("replace_me")
        or "your_id" in lowered
        or lowered in {"changeme", "change_me", "placeholder"}
    )


def safe_max_file_size_mb(raw_value: str | None) -> int:
    """Parse and sanitize max file size in MB.
    
    Args:
        raw_value (str | None): Parameter raw_value.
    
    Returns:
        int: And sanitize max file size in MB.
    """
    try:
        parsed = int(str(raw_value or "25").strip())
    except (TypeError, ValueError):
        return 25
    return parsed if parsed > 0 else 25


def refresh_runtime_config_from_env() -> None:
    """Refresh ImageKit/Supabase runtime clients from environment values.
    
    Returns:
        None: None.
    """
    context.IMAGEKIT_PRIVATE_KEY = os.getenv("IMAGEKIT_PRIVATE_KEY")
    context.IMAGEKIT_PUBLIC_KEY = os.getenv("IMAGEKIT_PUBLIC_KEY")
    context.IMAGEKIT_URL = os.getenv("IMAGEKIT_URL")
    context.SUPABASE_URL = os.getenv("SUPABASE_URL")
    context.SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    context.MAX_FILE_SIZE_MB = safe_max_file_size_mb(os.getenv("MAX_FILE_SIZE_MB"))
    context.MAX_FILE_SIZE = context.MAX_FILE_SIZE_MB * 1024 * 1024

    if (
        is_placeholder_secret(context.IMAGEKIT_PRIVATE_KEY)
        or is_placeholder_secret(context.IMAGEKIT_PUBLIC_KEY)
        or is_placeholder_secret(context.IMAGEKIT_URL)
    ):
        context.imagekit = None
    else:
        context.imagekit = ImageKit(
            private_key=context.IMAGEKIT_PRIVATE_KEY,
            public_key=context.IMAGEKIT_PUBLIC_KEY,
            url_endpoint=context.IMAGEKIT_URL,
        )

    if context.SUPABASE_URL and context.SUPABASE_KEY:
        try:
            context.supabase = create_client(
                context.SUPABASE_URL,
                context.SUPABASE_KEY,
                options=ClientOptions(auto_refresh_token=False, persist_session=False),
            )
        except Exception as exc:
            context.logger.warning(
                "Failed to initialize Supabase client from current env: %s",
                exc,
            )
            context.supabase = None
    else:
        context.supabase = None
