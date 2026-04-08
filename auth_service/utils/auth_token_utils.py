"""Token and metadata helpers for auth workflows."""

from typing import Any


def extract_auth_metadata(auth_user: Any) -> dict:
    """Extract safe user metadata from Supabase auth user object.
    
    Args:
        auth_user (Any): Parameter auth_user.
    
    Returns:
        dict: Safe user metadata from Supabase auth user object.
    """
    if auth_user is None:
        return {}
    if isinstance(auth_user, dict):
        metadata = auth_user.get("user_metadata") or {}
        return dict(metadata) if isinstance(metadata, dict) else {}

    metadata = getattr(auth_user, "user_metadata", None) or {}
    return dict(metadata) if isinstance(metadata, dict) else {}


def coerce_bool(value: Any) -> bool | None:
    """Convert loose flag values to ``bool`` when possible.
    
    Args:
        value (Any): Parameter value.
    
    Returns:
        bool | None: Loose flag values to ``bool`` when possible.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on", "enabled"}:
            return True
        if normalized in {"0", "false", "no", "off", "disabled", ""}:
            return False
        return None
    return bool(value)


def is_2fa_enabled(user: dict | None, auth_user: Any = None) -> bool:
    """Resolve whether 2FA is enabled from profile and auth metadata.
    
    Args:
        user (dict | None): Parameter user.
        auth_user (Any): Parameter auth_user.
    
    Returns:
        bool: True if 2fa enabled, otherwise False.
    """
    metadata = extract_auth_metadata(auth_user)
    sources = (user or {}, metadata)

    for source in sources:
        if "is_2fa_enabled" in source:
            parsed = coerce_bool(source.get("is_2fa_enabled"))
            if parsed is not None:
                return parsed

    for source in sources:
        for flag_column in ("totp_enabled", "twofa_enabled"):
            value = source.get(flag_column)
            if value is not None:
                parsed = coerce_bool(value)
                if parsed is not None:
                    return parsed
                return bool(value)

    for source in sources:
        if extract_totp_secret(source):
            return True

    return False


def extract_totp_secret(source: dict | None) -> str | None:
    """Return first available TOTP secret from known columns.
    
    Args:
        source (dict | None): Parameter source.
    
    Returns:
        str | None: First available TOTP secret from known columns.
    """
    for secret_column in ("totp_secret", "twofa_secret", "otp_secret"):
        value = (source or {}).get(secret_column)
        if value:
            return str(value)
    return None


def normalized_email(email: str | None) -> str:
    """Normalize email values for case-insensitive comparisons.
    
    Args:
        email (str | None): Parameter email.
    
    Returns:
        str: Email values for case-insensitive comparisons.
    """
    return (email or "").strip().lower()
