"""Media metadata storage helpers."""

from uuid import UUID

from fastapi import HTTPException
from postgrest.exceptions import APIError

from core import context
from services.runtime_access import ensure_supabase_configured


def insert_media_record(
    user_id: str,
    url: str,
    imagekit_file_id: str,
    detected_type: str,
    size_mb: float,
) -> dict:
    """Insert media metadata row and return created record.
    
    Args:
        user_id (str): User identifier.
        url (str): Target URL.
        imagekit_file_id (str): Identifier for imagekit file.
        detected_type (str): Parameter detected_type.
        size_mb (float): Parameter size_mb.
    
    Returns:
        dict: Result of the operation.
    """
    db = ensure_supabase_configured()
    payload = {
        "user_id": user_id,
        "url": url,
        "file_id": imagekit_file_id,
        "detected_type": detected_type,
        "size_mb": size_mb,
    }

    try:
        inserted = db.table(context.MEDIA_FILES_TABLE).insert(payload).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to store media metadata: {exc}") from exc

    rows = inserted.data or []
    if rows:
        return rows[0]

    try:
        fetched = (
            db.table(context.MEDIA_FILES_TABLE)
            .select("*")
            .eq("file_id", imagekit_file_id)
            .limit(1)
            .execute()
        )
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch stored media metadata: {exc}") from exc

    fetched_rows = fetched.data or []
    if not fetched_rows:
        raise HTTPException(status_code=502, detail="Media metadata was not returned by database")
    return fetched_rows[0]


def get_media_record_by_reference(file_ref: str) -> dict | None:
    """Load one media record by UUID id or ImageKit file_id.
    
    Args:
        file_ref (str): Parameter file_ref.
    
    Returns:
        dict | None: Retrieved value.
    """
    db = ensure_supabase_configured()
    is_uuid_ref = True
    try:
        UUID(file_ref)
    except ValueError:
        is_uuid_ref = False

    try:
        query = db.table(context.MEDIA_FILES_TABLE).select("*")
        query = query.eq("id", file_ref) if is_uuid_ref else query.eq("file_id", file_ref)
        result = query.limit(1).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch media metadata: {exc}") from exc

    rows = result.data or []
    return rows[0] if rows else None


def delete_media_record(media_id: str) -> None:
    """Delete one media metadata row by UUID.
    
    Args:
        media_id (str): Media identifier.
    
    Returns:
        None: None.
    """
    db = ensure_supabase_configured()
    try:
        db.table(context.MEDIA_FILES_TABLE).delete().eq("id", media_id).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to delete media metadata: {exc}") from exc
