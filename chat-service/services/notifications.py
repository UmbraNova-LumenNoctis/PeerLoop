"""Notification helper for chat events."""

import httpx

from core.context import (
    INTERNAL_SERVICE_TOKEN,
    INTERNAL_TLS_VERIFY,
    NOTIFICATION_SERVICE_URL,
    NOTIFICATION_TIMEOUT_SECONDS,
    logger,
)


def send_notification(
    target_user_id: str,
    notification_type: str,
    content: str | None = None,
    source_id: str | None = None,
) -> None:
    """Send best-effort internal notification.
    
    Args:
        target_user_id (str): Identifier for target user.
        notification_type (str): Parameter notification_type.
        content (str | None): Text content.
        source_id (str | None): Identifier for source.
    
    Returns:
        None: None.
    """
    if not INTERNAL_SERVICE_TOKEN or not NOTIFICATION_SERVICE_URL:
        return

    payload: dict[str, str] = {"user_id": target_user_id, "type": notification_type}
    if content is not None:
        payload["content"] = content
    if source_id is not None:
        payload["source_id"] = source_id

    try:
        response = httpx.post(
            f"{NOTIFICATION_SERVICE_URL.rstrip('/')}/notifications/internal",
            headers={"x-internal-service-token": INTERNAL_SERVICE_TOKEN},
            json=payload,
            timeout=NOTIFICATION_TIMEOUT_SECONDS,
            verify=INTERNAL_TLS_VERIFY,
        )
    except Exception as exc:
        logger.warning("Notification request failed: %s", exc)
        return

    if response.status_code not in (200, 201):
        logger.warning(
            "Notification request returned status %s: %s",
            response.status_code,
            response.text,
        )
