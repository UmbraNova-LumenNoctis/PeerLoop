from fastapi import APIRouter, Depends, Request
from routers.auth import proxy_request
from routers.security import require_bearer_token

twofa_router = APIRouter(prefix="/api/2fa", tags=["2FA"])

@twofa_router.post("/enable", summary="Enable 2FA for user",
                    description="Generate TOTP secret and QR code")
async def enable_2fa(request: Request, _: str = Depends(require_bearer_token)):
    """Start 2FA enrollment by requesting a TOTP secret and QR payload.
    
    Args:
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Result of the operation.
    """
    return await proxy_request(
        method="POST",
        path="2fa/enable",
        headers=request.headers,
        params=request.query_params,
    )

@twofa_router.post("/verify", summary="Verify 2FA code",
                    description="Verify TOTP code and activate 2FA")
async def verify_2fa(request: Request, _: str = Depends(require_bearer_token)):
    """Verify a submitted TOTP code and activate 2FA.
    
    Args:
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Result of the operation.
    """
    json_body = None
    try:
        json_body = await request.json()
    except Exception:
        json_body = None

    return await proxy_request(
        method="POST",
        path="2fa/verify",
        json_body=json_body,
        headers=request.headers,
        params=request.query_params,
    )


@twofa_router.get("/status", summary="Get 2FA status",
                  description="Returns current 2FA state for the authenticated user")
async def get_2fa_status(request: Request, _: str = Depends(require_bearer_token)):
    """Fetch the current 2FA activation status for the authenticated user.
    
    Args:
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Current 2FA activation status for the authenticated user.
    """
    return await proxy_request(
        method="GET",
        path="2fa/status",
        headers=request.headers,
        params=request.query_params,
    )


@twofa_router.post("/disable", summary="Disable 2FA",
                   description="Disable TOTP 2FA for the authenticated user")
async def disable_2fa(request: Request, _: str = Depends(require_bearer_token)):
    """Disable TOTP-based 2FA for the authenticated user.
    
    Args:
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Result of the operation.
    """
    return await proxy_request(
        method="POST",
        path="2fa/disable",
        headers=request.headers,
        params=request.query_params,
    )
