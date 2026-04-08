"""Media response serialization helpers."""


def preview_url_for(url: str, detected_type: str | None) -> str:
    """Build preview URL for image assets.
    
    Args:
        url (str): Target URL.
        detected_type (str | None): Parameter detected_type.
    
    Returns:
        str: Preview URL for image assets.
    """
    if not url:
        return url

    media_type = (detected_type or "").lower()
    if media_type.startswith("image/"):
        return f"{url}?tr=w-800,h-800,c-at_max"
    return url


def size_mb_to_bytes(size_mb_value) -> int | None:
    """Convert megabytes value to rounded bytes.
    
    Args:
        size_mb_value (Any): Parameter size_mb_value.
    
    Returns:
        int | None: Megabytes value to rounded bytes.
    """
    if size_mb_value is None:
        return None

    try:
        value = float(size_mb_value)
    except (TypeError, ValueError):
        return None
    if value < 0:
        return None
    return int(round(value * 1024 * 1024))


def serialize_media_row(row: dict) -> dict:
    """Serialize media row to API response payload.
    
    Args:
        row (dict): Parameter row.
    
    Returns:
        dict: Media row to API response payload.
    """
    detected_type = row.get("detected_type")
    url = row.get("url")
    size_mb = row.get("size_mb")
    return {
        "id": row.get("id"),
        "media_id": row.get("id"),
        "uuid": row.get("id"),
        "url": url,
        "preview_url": preview_url_for(url, detected_type),
        "file_id": row.get("file_id"),
        "detected_type": detected_type,
        "size_mb": size_mb,
        "size_bytes": size_mb_to_bytes(size_mb),
        "created_at": row.get("created_at"),
        "user_id": row.get("user_id"),
    }
