"""OAuth and callback routes for Auth API."""

from fastapi import APIRouter, Request
from fastapi.responses import Response

from routers.auth import proxy_request

auth_oauth_router = APIRouter()
oauth_public_router = APIRouter()


@auth_oauth_router.get(
    "/google",
    summary="Google OAuth login URL",
    description="Get Google OAuth login URL via Auth Service",
)
async def google_login(request: Request) -> Response:
    """Return the Google OAuth authorization URL from Auth Service.
    
    Args:
        request (Request): Incoming FastAPI request context.
    
    Returns:
        Response: Google OAuth authorization URL from Auth Service.
    """
    return await proxy_request(
        method="GET",
        path="auth/login/google",
        headers=request.headers,
        params=request.query_params,
    )


@auth_oauth_router.get(
    "/google/callback",
    summary="Google OAuth callback",
    description="Handle Google OAuth callback via Auth Service",
)
async def google_callback(request: Request) -> Response:
    """Forward Google OAuth callback query parameters to Auth Service.
    
    Args:
        request (Request): Incoming FastAPI request context.
    
    Returns:
        Response: Result of the operation.
    """
    return await proxy_request(
        method="GET",
        path="auth/google/callback",
        headers=request.headers,
        params=request.query_params,
    )


@oauth_public_router.get(
    "/auth/google/callback",
    summary="Google OAuth callback (public path)",
    description="Compatibility callback path for Google OAuth redirect URI",
)
async def google_callback_public(request: Request) -> Response:
    """Public compatibility callback used by external OAuth redirect URIs.
    
    Args:
        request (Request): Incoming FastAPI request context.
    
    Returns:
        Response: Result of the operation.
    """
    return await proxy_request(
        method="GET",
        path="auth/google/callback",
        headers=request.headers,
        params=request.query_params,
    )


@auth_oauth_router.get(
    "/email/confirm",
    summary="Email confirmation callback",
    description="Handle Supabase email confirmation redirect via Auth Service",
)
async def email_confirm_callback(request: Request) -> Response:
    """Forward email confirmation callback to Auth Service.
    
    Args:
        request (Request): Incoming FastAPI request context.
    
    Returns:
        Response: Result of the operation.
    """
    return await proxy_request(
        method="GET",
        path="auth/email/confirm",
        headers=request.headers,
        params=request.query_params,
    )
