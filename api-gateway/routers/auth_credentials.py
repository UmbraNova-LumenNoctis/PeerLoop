"""Credential and session routes for Auth API."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from routers.auth import proxy_request
from shared_schemas.models import LoginRequest, SignupRequest

auth_credentials_router = APIRouter()


@auth_credentials_router.post(
    "/signup",
    summary="Create account",
    description="Validate and forward signup",
)
async def signup(payload: SignupRequest, request: Request) -> Response:
    """Create an account via Auth Service.
    
    Args:
        payload (SignupRequest): Parsed request payload.
        request (Request): Incoming FastAPI request context.
    
    Returns:
        Response: Account via Auth Service.
    """
    return await proxy_request(
        method="POST",
        path="auth/register",
        json_body=payload.model_dump(),
        headers=request.headers,
        params=request.query_params,
    )


@auth_credentials_router.post(
    "/login",
    summary="Login with email/password",
    description="Authenticate user via Auth Service",
)
async def login(payload: LoginRequest, request: Request) -> Response:
    """Authenticate user with credentials via Auth Service.
    
    Args:
        payload (LoginRequest): Parsed request payload.
        request (Request): Incoming FastAPI request context.
    
    Returns:
        Response: Result of the operation.
    """
    return await proxy_request(
        method="POST",
        path="auth/login",
        json_body=payload.model_dump(),
        headers=request.headers,
        params=request.query_params,
    )


@auth_credentials_router.post(
    "/login/2fa/verify",
    summary="Verify login 2FA challenge",
    description="Finalize email/password login by validating a pending 2FA challenge",
)
async def login_2fa_verify(request: Request) -> Response:
    """Finalize login by submitting second-factor challenge payload.
    
    Args:
        request (Request): Incoming FastAPI request context.
    
    Returns:
        Response: Result of the operation.
    """
    try:
        body = await request.json()
    except Exception as exc:  # pragma: no cover - defensive gateway check
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    return await proxy_request(
        method="POST",
        path="auth/login/2fa/verify",
        json_body=body,
        headers=request.headers,
        params=request.query_params,
    )


@auth_credentials_router.post(
    "/session/exchange",
    summary="Accept callback session",
    description="Exchange callback access/refresh tokens and persist refresh cookie via Auth Service",
)
async def session_exchange(request: Request) -> Response:
    """Exchange callback tokens for gateway session via Auth Service.
    
    Args:
        request (Request): Incoming FastAPI request context.
    
    Returns:
        Response: Result of the operation.
    """
    try:
        body = await request.json()
    except Exception as exc:  # pragma: no cover - defensive gateway check
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    return await proxy_request(
        method="POST",
        path="auth/session/exchange",
        json_body=body,
        headers=request.headers,
        params=request.query_params,
    )


@auth_credentials_router.post(
    "/refresh",
    summary="Refresh access token",
    description="Refresh access token via Auth Service using refresh token cookie",
)
async def refresh(request: Request) -> Response:
    """Refresh access token through Auth Service.
    
    Args:
        request (Request): Incoming FastAPI request context.
    
    Returns:
        Response: Result of the operation.
    """
    body = None
    content_type = (request.headers.get("content-type") or "").lower()
    if content_type.startswith("application/json"):
        try:
            body = await request.json()
        except Exception:
            body = None

    return await proxy_request(
        method="POST",
        path="auth/refresh",
        json_body=body,
        headers=request.headers,
        params=request.query_params,
    )
