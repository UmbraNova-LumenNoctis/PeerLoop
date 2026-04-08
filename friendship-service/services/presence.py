"""Presence lookup helpers for friendship projections."""

import httpx

from core.context import (
    CHAT_SERVICE_URL,
    INTERNAL_SERVICE_TOKEN,
    INTERNAL_TLS_VERIFY,
    NOTIFICATION_TIMEOUT_SECONDS,
    logger,
)


def get_online_user_ids(user_ids: list[str]) -> set[str]:
    """Return set of currently online user ids for the provided ids.
    
    Args:
        user_ids (list[str]): Identifiers for user.
    
    Returns:
        set[str]: Set of currently online user ids for the provided ids.
    """
    if not user_ids or not INTERNAL_SERVICE_TOKEN:
        return set()

    deduped_ids = sorted({user_id for user_id in user_ids if user_id})
    if not deduped_ids:
        return set()

    try:
        response = httpx.get(
            f"{CHAT_SERVICE_URL.rstrip('/')}/presence/internal",
            params={"user_ids": ",".join(deduped_ids)},
            headers={"x-internal-service-token": INTERNAL_SERVICE_TOKEN},
            timeout=NOTIFICATION_TIMEOUT_SECONDS,
            verify=INTERNAL_TLS_VERIFY,
        )
    except Exception as exc:
        logger.warning("Presence request failed: %s", exc)
        return set()

    if response.status_code != 200:
        logger.warning("Presence request returned status %s: %s", response.status_code, response.text)
        return set()

    try:
        payload = response.json()
    except Exception:
        return set()

    raw_ids = payload.get("online_user_ids", [])
    if not isinstance(raw_ids, list):
        return set()
    return {str(user_id) for user_id in raw_ids}
