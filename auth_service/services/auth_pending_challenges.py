"""In-memory pending 2FA login challenge management."""

import threading
import time
import uuid

from core.auth_context import PENDING_LOGIN_2FA_TTL_SECONDS

_pending_login_2fa_lock = threading.Lock()
_pending_login_2fa: dict[str, dict] = {}


def cleanup_expired_pending_login_2fa(now: float | None = None) -> None:
    """Remove expired pending login 2FA challenges from memory.
    
    Args:
        now (float | None): Parameter now.
    
    Returns:
        None: None.
    """
    current_ts = now if isinstance(now, (int, float)) else time.time()
    expired_challenge_ids = [
        challenge_id
        for challenge_id, payload in _pending_login_2fa.items()
        if (current_ts - float(payload.get("created_at") or 0))
        > PENDING_LOGIN_2FA_TTL_SECONDS
    ]
    for challenge_id in expired_challenge_ids:
        _pending_login_2fa.pop(challenge_id, None)


def create_pending_login_2fa_challenge(
    user_id: str,
    access_token: str,
    refresh_token: str | None,
) -> str:
    """Create and store a pending 2FA login challenge.
    
    Args:
        user_id (str): User identifier.
        access_token (str): Access token.
        refresh_token (str | None): Refresh token.
    
    Returns:
        str: And store a pending 2FA login challenge.
    """
    challenge_id = uuid.uuid4().hex
    with _pending_login_2fa_lock:
        cleanup_expired_pending_login_2fa()
        _pending_login_2fa[challenge_id] = {
            "user_id": str(user_id),
            "access_token": str(access_token),
            "refresh_token": str(refresh_token or ""),
            "created_at": time.time(),
        }
    return challenge_id


def get_pending_login_2fa_challenge(challenge_id: str) -> dict | None:
    """Read one pending 2FA login challenge.
    
    Args:
        challenge_id (str): Identifier for challenge.
    
    Returns:
        dict | None: Retrieved value.
    """
    with _pending_login_2fa_lock:
        cleanup_expired_pending_login_2fa()
        payload = _pending_login_2fa.get(challenge_id)
        return dict(payload) if payload else None


def delete_pending_login_2fa_challenge(challenge_id: str) -> None:
    """Delete one pending 2FA login challenge.
    
    Args:
        challenge_id (str): Identifier for challenge.
    
    Returns:
        None: None.
    """
    with _pending_login_2fa_lock:
        _pending_login_2fa.pop(challenge_id, None)
