"""Content normalization helpers."""


def normalize_content(content: str | None) -> str | None:
    """Trim whitespace and return None for empty content.
    
    Args:
        content (str | None): Text content.
    
    Returns:
        str | None: Validated value.
    """
    if content is None:
        return None

    normalized = content.strip()
    return normalized if normalized else None
