"""Message content normalization helpers."""


def normalize_content(content: str | None) -> str | None:
    """Normalize user message content and reject blank-only values.
    
    Args:
        content (str | None): Text content.
    
    Returns:
        str | None: User message content and reject blank-only values.
    """
    if content is None:
        return None
    normalized = content.strip()
    return normalized if normalized else None
