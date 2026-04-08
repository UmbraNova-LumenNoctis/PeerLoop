"""Runtime accessors that ensure file service dependencies are configured."""

from fastapi import HTTPException

from core import context
from core.context import PATHS_FILE_SERVICE, load_vault_secrets
from core.runtime_state import refresh_runtime_config_from_env


def reload_vault_backed_runtime_config() -> None:
    """Reload Vault secrets and refresh runtime clients atomically.
    
    Returns:
        None: None.
    """
    with context.runtime_config_lock:
        load_vault_secrets(PATHS_FILE_SERVICE)
        refresh_runtime_config_from_env()


def ensure_imagekit_configured():
    """Return configured ImageKit client or raise service configuration error.
    
    Returns:
        Any: Configured ImageKit client or raise service configuration error.
    """
    if context.imagekit is None:
        reload_vault_backed_runtime_config()

    if context.imagekit is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "File service is not configured: invalid ImageKit credentials "
                "in Vault (secret/imagekit)."
            ),
        )
    return context.imagekit


def ensure_supabase_configured():
    """Return configured Supabase client or raise service configuration error.
    
    Returns:
        Any: Configured Supabase client or raise service configuration error.
    """
    if not context.supabase:
        reload_vault_backed_runtime_config()
    if not context.supabase:
        raise HTTPException(
            status_code=503,
            detail="File service is not configured: missing Supabase credentials",
        )
    return context.supabase


refresh_runtime_config_from_env()
