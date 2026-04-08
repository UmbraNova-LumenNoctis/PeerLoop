"""Upload route for secure file service."""

import os
import tempfile

import magic
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions

from core import context
from core.auth_utils import verify_internal_request
from serializers.media_serialize import preview_url_for
from stores.media_store import insert_media_record
from services.notifications import send_notification
from services.runtime_access import ensure_imagekit_configured
from utils.validation import validate_file_metadata

upload_router = APIRouter()


def _rollback_uploaded_file(imagekit_client, uploaded_file_id: str | None) -> None:
    """Delete uploaded file in ImageKit on failure.
    
    Args:
        imagekit_client (Any): Parameter imagekit_client.
        uploaded_file_id (str | None): Identifier for uploaded file.
    
    Returns:
        None: None.
    """
    if not uploaded_file_id:
        return

    try:
        imagekit_client.delete_file(file_id=uploaded_file_id)
    except Exception:
        pass


def _detect_file_mime(temp_file_path: str) -> str:
    """Detect MIME type from temporary file path.
    
    Args:
        temp_file_path (str): Parameter temp_file_path.
    
    Returns:
        str: Result of the operation.
    """
    mime = magic.Magic(mime=True)
    return mime.from_file(temp_file_path)


def _validate_detected_mime(ext: str, content_type: str, detected_type: str) -> None:
    """Validate detected MIME type against extension allowlist.
    
    Args:
        ext (str): Parameter ext.
        content_type (str): Parameter content_type.
        detected_type (str): Parameter detected_type.
    
    Returns:
        None: None.
    """
    allowed_detected_types = context.ALLOWED_DETECTED_MIME_BY_EXTENSION.get(ext, {content_type})
    if detected_type not in allowed_detected_types:
        raise HTTPException(
            status_code=415,
            detail=f"Invalid file format detected: {detected_type}",
        )


async def _stream_upload_to_temp(file: UploadFile, ext: str) -> tuple[str, int]:
    """Write upload stream to temporary file and enforce size limit.
    
    Args:
        file (UploadFile): Parameter file.
        ext (str): Parameter ext.
    
    Returns:
        tuple[str, int]: Result of the operation.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
        temp_file_path = temp_file.name
        size = 0

        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > context.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large (max {context.MAX_FILE_SIZE_MB}MB)",
                )
            temp_file.write(chunk)

    return temp_file_path, size


@upload_router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user: dict = Depends(verify_internal_request),
):
    """Upload file to ImageKit and persist metadata in Supabase.
    
    Args:
        file (UploadFile): Parameter file.
        user (dict): Parameter user.
    
    Returns:
        Any: Result of the operation.
    """
    temp_file_path: str | None = None
    uploaded_file_id: str | None = None
    imagekit_client = ensure_imagekit_configured()

    try:
        ext = validate_file_metadata(file.filename, file.content_type)
        temp_file_path, size = await _stream_upload_to_temp(file, ext)

        detected_type = _detect_file_mime(temp_file_path)
        _validate_detected_mime(ext, file.content_type, detected_type)

        with open(temp_file_path, "rb") as file_stream:
            upload_result = imagekit_client.upload_file(
                file=file_stream,
                file_name=f"user_{user['id']}_{file.filename}",
                options=UploadFileRequestOptions(
                    use_unique_file_name=True,
                    tags=[f"user:{user['id']}", "secure-upload"],
                ),
            )

        if upload_result.response_metadata.http_status_code != 200:
            raise HTTPException(status_code=502, detail="Upload failed")

        uploaded_file_id = upload_result.file_id
        size_mb = round(size / (1024 * 1024), 2)
        media = insert_media_record(
            user_id=user["id"],
            url=upload_result.url,
            imagekit_file_id=uploaded_file_id,
            detected_type=detected_type,
            size_mb=size_mb,
        )
        send_notification(
            target_user_id=user["id"],
            notification_type="file_created",
            content="File uploaded successfully",
            source_id=str(media.get("id")) if media.get("id") else None,
        )

        media_url = media.get("url") or upload_result.url
        return JSONResponse(
            status_code=201,
            content={
                "message": "Upload successful",
                "id": media.get("id"),
                "media_id": media.get("id"),
                "uuid": media.get("id"),
                "url": media_url,
                "preview_url": preview_url_for(media_url, detected_type),
                "file_id": uploaded_file_id,
                "user_id": user["id"],
                "detected_type": detected_type,
                "size_mb": size_mb,
                "size_bytes": size,
                "created_at": media.get("created_at"),
            },
        )
    except HTTPException:
        _rollback_uploaded_file(imagekit_client, uploaded_file_id)
        raise
    except Exception as exc:
        _rollback_uploaded_file(imagekit_client, uploaded_file_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        await file.close()
