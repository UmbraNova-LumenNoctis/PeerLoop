"""Internal notification helper for file service."""

import httpx

from core import context


def is_internal_token_valid() -> bool:
    """Tell whether internal service token is configured.
    
    Returns:
        bool: True if internal token valid, otherwise False.
    """
    return bool(context.INTERNAL_SERVICE_TOKEN)


def send_notification(
    target_user_id: str,
    notification_type: str,
    content: str | None = None,
    source_id: str | None = None,
) -> None:
    """Send best-effort notification to notification service.
    
    Args:
        target_user_id (str): Identifier for target user.
        notification_type (str): Parameter notification_type.
        content (str | None): Text content.
        source_id (str | None): Identifier for source.
    
    Returns:
        None: None.
    """
    if not is_internal_token_valid() or not context.NOTIFICATION_SERVICE_URL:
        return

    payload: dict[str, str] = {"user_id": target_user_id, "type": notification_type}
    if content is not None:
        payload["content"] = content
    if source_id is not None:
        payload["source_id"] = source_id

    try:
        response = httpx.post(
            f"{context.NOTIFICATION_SERVICE_URL.rstrip('/')}/notifications/internal",
            headers={"x-internal-service-token": context.INTERNAL_SERVICE_TOKEN},
            json=payload,
            timeout=context.NOTIFICATION_TIMEOUT_SECONDS,
            verify=context.INTERNAL_TLS_VERIFY,
        )
    except Exception as exc:
        context.logger.warning("Notification request failed: %s", exc)
        return

    if response.status_code not in (200, 201):
        context.logger.warning(
            "Notification request returned status %s: %s",
            response.status_code,
            response.text,
        )
