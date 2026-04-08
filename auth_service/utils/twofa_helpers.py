"""Core helper functions for 2FA endpoints."""

from postgrest.exceptions import APIError

from core.twofa_context import FLAG_COLUMNS, SECRET_COLUMNS, new_supabase_client


def resolve_user_id(x_user_id: str | None, x_access_token: str | None) -> str | None:
    """Resolve current user id from trusted header or access token.
    
    Args:
        x_user_id (str | None): Identifier for x user.
        x_access_token (str | None): Parameter x_access_token.
    
    Returns:
        str | None: Current user id from trusted header or access token.
    """
    if x_user_id:
        return x_user_id
    if x_access_token:
        try:
            token_client = new_supabase_client()
            user_resp = token_client.auth.get_user(x_access_token)
            user_obj = getattr(user_resp, "user", None)
            if user_obj and getattr(user_obj, "id", None):
                return user_obj.id
        except Exception:
            return None
    return None


def extract_totp_secret(user: dict) -> str | None:
    """Extract first existing TOTP secret from profile payload.
    
    Args:
        user (dict): Parameter user.
    
    Returns:
        str | None: First existing TOTP secret from profile payload.
    """
    for column in SECRET_COLUMNS:
        value = user.get(column)
        if value:
            return value
    return None


def is_missing_column_error(exc: APIError, column: str) -> bool:
    """Tell whether PostgREST error references a missing schema column.
    
    Args:
        exc (APIError): Parameter exc.
        column (str): Parameter column.
    
    Returns:
        bool: True if missing column error, otherwise False.
    """
    message = str(exc).lower()
    return column.lower() in message and "schema cache" in message


def coerce_optional_bool(value) -> bool | None:
    """Convert loose values to bool while preserving unknowns as ``None``.
    
    Args:
        value (Any): Parameter value.
    
    Returns:
        bool | None: Loose values to bool while preserving unknowns as ``None``.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return bool(value)


def resolve_twofa_enabled(user: dict | None, metadata: dict | None) -> bool:
    """Resolve effective 2FA enabled state from profile and metadata.
    
    Args:
        user (dict | None): Parameter user.
        metadata (dict | None): Parameter metadata.
    
    Returns:
        bool: Effective 2FA enabled state from profile and metadata.
    """
    for source in (user or {}, metadata or {}):
        for flag_column in FLAG_COLUMNS:
            value = coerce_optional_bool(source.get(flag_column))
            if value is not None:
                return value
    return bool(extract_totp_secret(user or {}) or extract_totp_secret(metadata or {}))
