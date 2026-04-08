"""Auth proxy helpers and router composition for API gateway."""

import os
from typing import Any, Mapping

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL")
FILE_SERVICE_URL = os.getenv("FILE_SERVICE_URL")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL")
FRIENDSHIP_SERVICE_URL = os.getenv("FRIENDSHIP_SERVICE_URL")
POST_SERVICE_URL = os.getenv("POST_SERVICE_URL")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL")
CHAT_SERVICE_URL = os.getenv("CHAT_SERVICE_URL")
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL")
SEARCH_SERVICE_URL = os.getenv("SEARCH_SERVICE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
INTERNAL_TLS_VERIFY = (
    (os.getenv("INTERNAL_TLS_VERIFY") or "false").strip().lower()
    in {"1", "true", "yes", "on"}
)

auth_router = APIRouter(prefix="/api/auth", tags=["Auth"])
oauth_callback_router = APIRouter(tags=["Auth"])


async def _get_user_from_token(token: str) -> dict[str, Any] | None:
    """Validate Supabase JWT and return user payload or ``None``.
    
    Args:
        token (str): Access token.
    
    Returns:
        dict[str, Any] | None: Supabase JWT and return user payload or ``None``.
    """
    if not SUPABASE_URL or not token:
        return None

    url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/user"
    headers: dict[str, str] = {"Authorization": f"Bearer {token}"}
    if SUPABASE_KEY:
        headers["apikey"] = SUPABASE_KEY

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=5.0)
        except httpx.RequestError:
            return None

    if response.status_code != 200:
        return None

    try:
        payload = response.json()
    except ValueError:
        return None

    return payload if isinstance(payload, dict) else None


def _sanitize_headers(
    raw_headers: Mapping[str, str] | None,
    *,
    has_files: bool,
) -> dict[str, str]:
    """Remove hop-by-hop and gateway-controlled headers from upstream request.
    
    Args:
        raw_headers (Mapping[str, str] | None): Parameter raw_headers.
        has_files (bool): Flag indicating whether files.
    
    Returns:
        dict[str, str]: Result of the operation.
    """
    blocked_headers = {
        "host",
        "content-length",
        "transfer-encoding",
        "x-user-id",
        "x-user-email",
        "x-access-token",
    }
    if has_files:
        blocked_headers.add("content-type")

    safe_headers: dict[str, str] = {}
    for key, value in dict(raw_headers or {}).items():
        if key.lower() not in blocked_headers:
            safe_headers[key] = value
    return safe_headers


async def _inject_auth_identity(headers: dict[str, str]) -> None:
    """Attach token and optional user identity headers for downstream services.
    
    Args:
        headers (dict[str, str]): HTTP headers for the request.
    
    Returns:
        None: None.
    """
    authorization = next(
        (
            value
            for key, value in headers.items()
            if key.lower() == "authorization" and isinstance(value, str)
        ),
        None,
    )
    if not authorization or not authorization.lower().startswith("bearer "):
        return

    token = authorization.split(None, 1)[1]
    headers["x-access-token"] = token
    headers["authorization"] = f"Bearer {token}"

    user = await _get_user_from_token(token)
    if not user:
        return

    user_id = user.get("id")
    user_email = user.get("email")
    if isinstance(user_id, str):
        headers["x-user-id"] = user_id
    if isinstance(user_email, str):
        headers["x-user-email"] = user_email


def _build_proxy_response(response: httpx.Response) -> Response:
    """Convert upstream HTTPX response into FastAPI response.
    
    Args:
        response (httpx.Response): FastAPI response object to mutate.
    
    Returns:
        Response: Upstream HTTPX response into FastAPI response.
    """
    response_headers = {
        key: value
        for key, value in response.headers.items()
        if key.lower()
        not in {
            "transfer-encoding",
            "content-encoding",
            "connection",
            "content-length",
            "date",
            "server",
        }
    }

    content_type = (response.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        try:
            content: Any = response.json()
        except ValueError:
            content = response.text
        return JSONResponse(
            content=content,
            status_code=response.status_code,
            headers=response_headers,
        )

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=response_headers,
    )


async def proxy_request(
    method: str,
    path: str,
    json_body: Any | None = None,
    headers: Mapping[str, str] | None = None,
    params: Mapping[str, str] | None = None,
    raw_body: bytes | None = None,
    files_body: Any | None = None,
    base_url: str | None = None,
) -> Response:
    """Forward a request to upstream service while preserving gateway behavior.
    
    Args:
        method (str): HTTP method.
        path (str): Path or route string.
        json_body (Any | None): JSON payload to forward.
        headers (Mapping[str, str] | None): HTTP headers for the request.
        params (Mapping[str, str] | None): Query parameters.
        raw_body (bytes | None): Parameter raw_body.
        files_body (Any | None): Parameter files_body.
        base_url (str | None): URL for base.
    
    Returns:
        Response: Result of the operation.
    """
    safe_headers = _sanitize_headers(headers, has_files=files_body is not None)
    await _inject_auth_identity(safe_headers)

    upstream_base_url = (base_url or AUTH_SERVICE_URL or "").rstrip("/")
    if not upstream_base_url:
        raise HTTPException(status_code=500, detail="AUTH_SERVICE_URL is not configured")

    upstream_url = f"{upstream_base_url}/{path.lstrip('/')}"
    request_kwargs: dict[str, Any] = {
        "method": method,
        "url": upstream_url,
        "headers": safe_headers,
        "params": params,
        "timeout": 20.0,
    }

    if raw_body is not None:
        request_kwargs["content"] = raw_body
    elif files_body is not None:
        request_kwargs["files"] = files_body
    else:
        request_kwargs["json"] = json_body

    async with httpx.AsyncClient(verify=INTERNAL_TLS_VERIFY) as client:
        try:
            response = await client.request(**request_kwargs)
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Upstream service unreachable: {exc}",
            ) from exc

    return _build_proxy_response(response)


from routers.auth_credentials import auth_credentials_router
from routers.auth_oauth import auth_oauth_router, oauth_public_router

auth_router.include_router(auth_credentials_router)
auth_router.include_router(auth_oauth_router)
oauth_callback_router.include_router(oauth_public_router)
