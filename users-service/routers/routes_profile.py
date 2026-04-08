"""User profile route handlers."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException
from postgrest.exceptions import APIError

from core.context import supabase_admin
from core.identity import resolve_identity
from services.media import to_profile_response, validate_media_exists
from schemas.models import UserProfileResponse, UserProfileUpdate
from services.notifications import send_notification
from stores.profile_store import (
    create_profile_if_missing,
    get_user_row_by_id,
    is_pseudo_already_used,
    sync_profile_if_needed,
)

user_profile_router = APIRouter()


@user_profile_router.get("/me", response_model=UserProfileResponse, summary="Get my profile")
def get_me(x_user_id: str = Header(None), x_user_email: str = Header(None), x_access_token: str = Header(None)):
    """Return current authenticated user's profile.
    
    Args:
        x_user_id (str): Identifier for x user.
        x_user_email (str): Parameter x_user_email.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Current authenticated user's profile.
    """
    resolved_user_id, resolved_email, token_metadata = resolve_identity(x_user_id, x_user_email, x_access_token)
    if not resolved_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: missing or invalid access token")

    user_row = get_user_row_by_id(resolved_user_id)
    created_profile = False
    if not user_row:
        user_row = create_profile_if_missing(resolved_user_id, resolved_email, token_metadata)
        created_profile = bool(user_row)
    if not user_row:
        raise HTTPException(status_code=404, detail="User profile not found")

    user_row = sync_profile_if_needed(
        user_row=user_row,
        user_id=resolved_user_id,
        email=resolved_email,
        metadata=token_metadata,
    )

    if created_profile:
        send_notification(
            target_user_id=resolved_user_id,
            notification_type="profile_created",
            content="Your profile was created",
            source_id=resolved_user_id,
        )

    return to_profile_response(user_row)


@user_profile_router.patch("/me", response_model=UserProfileResponse, summary="Update my profile")
def update_me(
    payload: UserProfileUpdate,
    x_user_id: str = Header(None),
    x_user_email: str = Header(None),
    x_access_token: str = Header(None),
):
    """Update current authenticated user's editable profile fields.
    
    Args:
        payload (UserProfileUpdate): Parsed request payload.
        x_user_id (str): Identifier for x user.
        x_user_email (str): Parameter x_user_email.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Result of the operation.
    """
    resolved_user_id, resolved_email, token_metadata = resolve_identity(x_user_id, x_user_email, x_access_token)
    if not resolved_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: missing or invalid access token")

    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    if not updates:
        user_row = get_user_row_by_id(resolved_user_id) or create_profile_if_missing(
            resolved_user_id,
            resolved_email,
            token_metadata,
        )
        if not user_row:
            raise HTTPException(status_code=404, detail="User profile not found")
        user_row = sync_profile_if_needed(
            user_row=user_row,
            user_id=resolved_user_id,
            email=resolved_email,
            metadata=token_metadata,
        )
        return to_profile_response(user_row)

    if "pseudo" in updates and updates["pseudo"] is not None:
        pseudo = updates["pseudo"].strip()
        if not pseudo:
            raise HTTPException(status_code=422, detail="Pseudo cannot be empty")
        if is_pseudo_already_used(pseudo, resolved_user_id):
            raise HTTPException(status_code=409, detail="Pseudo already in use")
        updates["pseudo"] = pseudo

    avatar_media_url: str | None = None
    cover_media_url: str | None = None

    if "avatar_id" in updates and updates["avatar_id"] is not None:
        avatar_id = str(updates["avatar_id"])
        avatar_media_url = validate_media_exists(avatar_id, "Avatar")
        updates["avatar_id"] = avatar_id

    if "cover_id" in updates and updates["cover_id"] is not None:
        cover_id = str(updates["cover_id"])
        cover_media_url = validate_media_exists(cover_id, "Cover")
        updates["cover_id"] = cover_id

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    fallback_updates = dict(updates)

    try:
        updated = supabase_admin.table("users").update(updates).eq("id", resolved_user_id).execute()
    except APIError as exc:
        message = str(exc).lower()
        if "duplicate" in message and "pseudo" in message:
            raise HTTPException(status_code=409, detail="Pseudo already in use")

        missing_avatar_column = "could not find the 'avatar_id' column" in message
        missing_cover_column = "could not find the 'cover_id' column" in message
        if not (missing_avatar_column or missing_cover_column):
            raise HTTPException(status_code=502, detail=f"Profile update failed: {exc}") from exc

        if missing_avatar_column:
            fallback_updates.pop("avatar_id", None)
            if avatar_media_url:
                fallback_updates["avatar_url"] = avatar_media_url

        if missing_cover_column:
            fallback_updates.pop("cover_id", None)
            if cover_media_url:
                fallback_updates["cover_url"] = cover_media_url

        if fallback_updates == updates:
            raise HTTPException(
                status_code=500,
                detail="Users table is missing profile media columns (avatar_id/cover_id). Apply latest SQL migration.",
            )

        try:
            updated = supabase_admin.table("users").update(fallback_updates).eq("id", resolved_user_id).execute()
        except APIError as fallback_error:
            fallback_message = str(fallback_error).lower()
            if (
                "could not find the 'cover_url' column" in fallback_message
                or "could not find the 'avatar_url' column" in fallback_message
            ):
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Users table is missing profile media columns "
                        "(avatar_id/avatar_url/cover_id/cover_url). Apply latest SQL migration."
                    ),
                )
            raise HTTPException(status_code=502, detail=f"Profile update failed: {fallback_error}") from fallback_error

    updated_rows = updated.data or []
    user_row = updated_rows[0] if updated_rows else get_user_row_by_id(resolved_user_id)
    if not user_row:
        raise HTTPException(status_code=404, detail="User profile not found")

    send_notification(
        target_user_id=resolved_user_id,
        notification_type="profile_updated",
        content="Your profile was updated",
        source_id=resolved_user_id,
    )
    return to_profile_response(user_row)


@user_profile_router.get("/{user_id}", response_model=UserProfileResponse, summary="Get profile by user id")
def get_user_profile(user_id: UUID, x_access_token: str = Header(None)):
    """Return one public user profile by identifier.
    
    Args:
        user_id (UUID): User identifier.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: One public user profile by identifier.
    """
    resolved_user_id, _, _ = resolve_identity(None, None, x_access_token)
    if not resolved_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: missing or invalid access token")

    user_row = get_user_row_by_id(str(user_id))
    if not user_row:
        raise HTTPException(status_code=404, detail="User profile not found")

    return to_profile_response(user_row)
