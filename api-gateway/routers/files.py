"""File upload routes proxied through API gateway."""

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import Response

from routers.auth import FILE_SERVICE_URL, proxy_request
from routers.security import require_bearer_token

file_router = APIRouter(prefix="/api/files", tags=["Files"])


@file_router.post(
    "/upload",
    summary="Upload file",
    description="Proxy multipart upload to File Service (returns media_id UUID + file_id)",
)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    _: str = Depends(require_bearer_token),
) -> Response:
    """Read incoming file stream and forward multipart payload to File Service.
    
    Args:
        request (Request): Incoming FastAPI request context.
        file (UploadFile): Parameter file.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Response: Result of the operation.
    """
    file_bytes = await file.read()
    return await proxy_request(
        method="POST",
        path="upload",
        files_body={
            "file": (file.filename, file_bytes, file.content_type),
        },
        headers=request.headers,
        params=request.query_params,
        base_url=FILE_SERVICE_URL,
    )
