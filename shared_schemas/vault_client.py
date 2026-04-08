"""
Vault secret loader for peerloop microservices.

Usage (at the TOP of each service's main.py, BEFORE router imports):

    from shared_schemas.vault_client import load_vault_secrets
    load_vault_secrets([
        "secret/supabase",
        "secret/google-oauth",
        "secret/app",
    ])
    from routers import auth, user  # routers call os.getenv() at module level

How it works:
  - Connects to Vault using VAULT_ADDR + VAULT_TOKEN (already set by docker-compose)
  - Reads each KV-v2 path and injects every key/value into os.environ
  - Existing env vars are NEVER overwritten (docker-compose environment: blocks win)
  - If Vault is unreachable the service still starts; missing secrets will surface
    later as individual errors (useful during local dev without Vault).
"""

import logging
import os
import time

logger = logging.getLogger(__name__)


def _resolve_vault_verify(vault_addr: str | None) -> bool | str:
    """Resolve TLS verification policy for Vault HTTP client.
    
    - "true/1/yes/on"  -> True
    - "false/0/no/off" -> False
    - any other value   -> interpreted as CA bundle path
    - unset             -> False for https:// VAULT_ADDR, True otherwise
    
    Args:
        vault_addr (str | None): Parameter vault_addr.
    
    Returns:
        bool | str: TLS verification policy for Vault HTTP client.
    """
    raw_verify = (os.getenv("VAULT_TLS_VERIFY") or "").strip()
    if raw_verify:
        lowered = raw_verify.lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
        return raw_verify
    if (vault_addr or "").lower().startswith("https://"):
        return False
    return True

# ---------------------------------------------------------------------------
# Canonical Vault paths used across all services
# ---------------------------------------------------------------------------
# Each constant is a list of paths that a given service typically needs.

PATHS_AUTH = [
    "secret/supabase",       # SUPABASE_URL, SUPABASE_KEY
    "secret/google-oauth",   # GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, REDIRECT_URI, …
    "secret/app",            # GATEWAY_SECRET, INTERNAL_SERVICE_TOKEN, ENV
]

PATHS_FILE_SERVICE = [
    "secret/supabase",
    "secret/imagekit",    # IMAGEKIT_PRIVATE_KEY, IMAGEKIT_PUBLIC_KEY, IMAGEKIT_URL
    "secret/app",
]

PATHS_USERS_SERVICE = [
    "secret/supabase",
    "secret/app",
]

PATHS_FRIENDSHIP_SERVICE = [
    "secret/supabase",
    "secret/app",
]

PATHS_POST_SERVICE = [
    "secret/supabase",
    "secret/app",
]

PATHS_NOTIFICATION_SERVICE = [
    "secret/supabase",
    "secret/app",
]

PATHS_CHAT_SERVICE = [
    "secret/supabase",
    "secret/app",
]

PATHS_LLM_SERVICE = [
    "secret/supabase",
    "secret/app",
    "secret/llm",   # GEMINI_API_KEY, GEMINI_MODEL, LLM_TIMEOUT_SECONDS, …
]

PATHS_SEARCH_SERVICE = [
    "secret/supabase",
    "secret/app",
]

PATHS_API_GATEWAY = [
    "secret/supabase",       # SUPABASE_URL, SUPABASE_KEY (for JWT validation in gateway)
    "secret/app",            # GATEWAY_SECRET, INTERNAL_SERVICE_TOKEN
]


# ---------------------------------------------------------------------------
# Core loader
# ---------------------------------------------------------------------------

def load_vault_secrets(paths: list[str]) -> None:
    """Fetch all secrets from the given Vault KV-v2 paths and inject them.
    
    into os.environ.
    
    ----------
    paths : list[str]
        List of "<mount_point>/<secret_name>" strings, e.g.:
            ["secret/supabase", "secret/google-oauth", "secret/app"]
    
    Args:
        paths (list[str]): Parameter paths.
    
    Returns:
        None: None.
    """
    vault_addr  = os.getenv("VAULT_ADDR")
    vault_token = os.getenv("VAULT_TOKEN")

    try:
        import hvac  # noqa: PLC0415
    except ImportError:
        logger.warning(
            "hvac not installed – Vault secret loading disabled. "
            "Add 'hvac' to requirements.txt to enable it."
        )
        return

    # ---- connect --------------------------------------------------------
    try:
        client = hvac.Client(
            url=vault_addr,
            token=vault_token,
            verify=_resolve_vault_verify(vault_addr),
        )
        if not client.is_authenticated():
            logger.error(
                "Vault authentication failed (addr=%s) – secrets NOT loaded. "
                "Check VAULT_TOKEN.",
                vault_addr,
            )
            return
    except Exception as exc:
        logger.error(
            "Cannot reach Vault at %s: %s – secrets NOT loaded. "
            "Service will fall back to existing env vars.",
            vault_addr, exc,
        )
        return

    # ---- fetch each path ------------------------------------------------
    for path in paths:
        parts       = path.split("/", 1)
        mount_point = parts[0]
        kv_path     = parts[1] if len(parts) > 1 else path

        last_error = None
        for attempt in range(1, 4):
            try:
                resp = client.secrets.kv.v2.read_secret_version(
                    path=kv_path,
                    mount_point=mount_point,
                    raise_on_deleted_version=True,
                )
                data: dict = resp["data"]["data"]
                injected: list[str] = []

                for key, value in data.items():
                    # Allow Vault to fill missing OR blank env variables.
                    current_value = os.environ.get(key)
                    if current_value is None or str(current_value).strip() == "":
                        os.environ[key] = str(value)
                        injected.append(key)

                logger.info("Vault[%s] loaded: %s", path, injected if injected else "nothing new")
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                if attempt < 3:
                    time.sleep(0.6)

        if last_error is not None:
            logger.warning("Vault[%s] could not be loaded: %s", path, last_error)
