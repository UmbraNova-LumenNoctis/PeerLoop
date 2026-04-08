"""File metadata validation helpers."""

import os

from fastapi import HTTPException

from core import context


def validate_file_metadata(filename: str, content_type: str) -> str:
    """Validate filename extension and declared content type.
    
    Args:
        filename (str): Parameter filename.
        content_type (str): Parameter content_type.
    
    Returns:
        str: Filename extension and declared content type.
    """
    if not filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    ext = os.path.splitext(filename)[1].lower()
    if ext not in context.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Invalid file extension")
    if content_type not in context.ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=415, detail="Invalid content type")

    return ext
