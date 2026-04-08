"""User profile route handlers."""

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Path
from pydantic import EmailStr, constr

from stores.user_identity import resolve_identity, select_user_profile_by_id
from stores.user_profile import build_profile_payload, sync_user_profile_row

user_routes_router = APIRouter()


@user_routes_router.get(
    "/me",
    summary="Get current user profile",
    description="Returns current user profile data (id, pseudo, email, avatar, bio).",
)
def me(
    x_user_id: Optional[constr(min_length=1)] = Header(None),
    x_user_email: Optional[EmailStr] = Header(None),
    x_access_token: Optional[str] = Header(None),
):
    """Return profile of the authenticated user.
    
    Args:
        x_user_id (Optional[constr(min_length=1)]): Identifier for x user.
        x_user_email (Optional[EmailStr]): Parameter x_user_email.
        x_access_token (Optional[str]): Parameter x_access_token.
    
    Returns:
        Any: Profile of the authenticated user.
    """
    resolved_user_id, resolved_email, token_metadata = resolve_identity(
        x_user_id=str(x_user_id) if x_user_id else None,
        x_user_email=str(x_user_email) if x_user_email else None,
        x_access_token=x_access_token,
    )
    if not resolved_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: provide a valid Bearer token")

    user_row = sync_user_profile_row(
        user_id=resolved_user_id,
        email=resolved_email,
        user_metadata=token_metadata,
    )
    return build_profile_payload(user_row, resolved_user_id, resolved_email)


@user_routes_router.get(
    "/{user_id}",
    summary="Get user profile by id",
    description="Returns public profile data for a user id.",
)
def user_by_id(
    user_id: str = Path(..., min_length=1),
    x_access_token: Optional[str] = Header(None),
    x_user_id: Optional[constr(min_length=1)] = Header(None),
    x_user_email: Optional[EmailStr] = Header(None),
):
    """Return public profile for one user id.
    
    Args:
        user_id (str): User identifier.
        x_access_token (Optional[str]): Parameter x_access_token.
        x_user_id (Optional[constr(min_length=1)]): Identifier for x user.
        x_user_email (Optional[EmailStr]): Parameter x_user_email.
    
    Returns:
        Any: Public profile for one user id.
    """
    resolved_user_id, _resolved_email, _token_metadata = resolve_identity(
        x_user_id=str(x_user_id) if x_user_id else None,
        x_user_email=str(x_user_email) if x_user_email else None,
        x_access_token=x_access_token,
    )
    if not resolved_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: provide a valid Bearer token")

    user_row = select_user_profile_by_id(user_id)
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")

    return build_profile_payload(
        user_row,
        user_id=str(user_row.get("id") or user_id),
        email=str(user_row.get("email")) if user_row.get("email") else None,
    )
