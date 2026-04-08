from fastapi import APIRouter, Body, Depends, Request
from routers.auth import USER_SERVICE_URL, proxy_request
from routers.security import require_bearer_token
from shared_schemas.models import UserProfileUpdateRequest

user_router = APIRouter(prefix="/api/user", tags=["User"])

@user_router.get("/me", summary="Get current user info",
                 description="Returns user_id and email from headers")
async def me(request: Request, _: str = Depends(require_bearer_token)):
    """Fetch the current authenticated user's profile from users service.
    
    Args:
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Current authenticated user's profile from users service.
    """
    return await proxy_request(
        method="GET",
        path="user/me",
        headers=request.headers,
        params=request.query_params,
        base_url=USER_SERVICE_URL,
    )


@user_router.patch("/me", summary="Update my profile",
                   description="Update profile fields (pseudo, address, bio, avatar_id, cover_id)")
async def update_me(
    request: Request,
    payload: UserProfileUpdateRequest | None = Body(default=None),
    _: str = Depends(require_bearer_token),
):
    """Update editable profile fields for the current user.
    
    Args:
        request (Request): Incoming FastAPI request context.
        payload (UserProfileUpdateRequest | None): Parsed request payload.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Result of the operation.
    """
    json_body = payload.model_dump(mode="json", exclude_unset=True, exclude_none=True) if payload else None
    return await proxy_request(
        method="PATCH",
        path="user/me",
        json_body=json_body,
        headers=request.headers,
        params=request.query_params,
        base_url=USER_SERVICE_URL,
    )


@user_router.get("/{user_id}", summary="Get user profile by id",
                 description="Get a user profile by UUID")
async def get_user_by_id(user_id: str, request: Request, _: str = Depends(require_bearer_token)):
    """Fetch a public user profile by user identifier.
    
    Args:
        user_id (str): User identifier.
        request (Request): Incoming FastAPI request context.
        _ (str): Unused dependency injection placeholder.
    
    Returns:
        Any: Public user profile by user identifier.
    """
    return await proxy_request(
        method="GET",
        path=f"user/{user_id}",
        headers=request.headers,
        params=request.query_params,
        base_url=USER_SERVICE_URL,
    )
