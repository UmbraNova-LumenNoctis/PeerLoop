"""Database profile persistence helpers."""

from typing import Any

from fastapi import HTTPException
from postgrest.exceptions import APIError

from core.context import supabase_admin


def get_user_row_by_id(user_id: str) -> dict | None:
    """Fetch one users table row by id.
    
    Args:
        user_id (str): User identifier.
    
    Returns:
        dict | None: One users table row by id.
    """
    try:
        result = supabase_admin.table("users").select("*").eq("id", user_id).limit(1).execute()
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"User lookup failed: {exc}") from exc

    rows = result.data or []
    return rows[0] if rows else None


def build_fallback_pseudo(user_id: str, email: str | None, metadata: dict[str, Any]) -> str:
    """Build a compact pseudo candidate from metadata/email.
    
    Args:
        user_id (str): User identifier.
        email (str | None): Parameter email.
        metadata (dict[str, Any]): Parameter metadata.
    
    Returns:
        str: Compact pseudo candidate from metadata/email.
    """
    candidate = metadata.get("username") or metadata.get("full_name") or metadata.get("name")
    if not isinstance(candidate, str) or not candidate.strip():
        candidate = email.split("@")[0] if isinstance(email, str) and "@" in email else None

    if not candidate:
        candidate = f"user_{user_id[:8]}"

    compact = "".join(ch for ch in candidate.strip() if ch.isalnum() or ch in {"_", "-", "."})
    if len(compact) < 3:
        compact = f"user_{user_id[:8]}"
    return compact[:30]


def create_profile_if_missing(user_id: str, email: str | None, metadata: dict[str, Any]) -> dict | None:
    """Insert profile row when absent, tolerating concurrent creation races.
    
    Args:
        user_id (str): User identifier.
        email (str | None): Parameter email.
        metadata (dict[str, Any]): Parameter metadata.
    
    Returns:
        dict | None: Constructed value.
    """
    payload: dict[str, Any] = {"id": user_id}
    if email:
        payload["email"] = email

    avatar_from_auth = metadata.get("avatar_url") or metadata.get("picture")
    cover_from_auth = metadata.get("cover_url")
    if isinstance(avatar_from_auth, str) and avatar_from_auth.strip():
        payload["avatar_url"] = avatar_from_auth.strip()
    if isinstance(cover_from_auth, str) and cover_from_auth.strip():
        payload["cover_url"] = cover_from_auth.strip()

    pseudo_candidate = build_fallback_pseudo(user_id, email, metadata)
    try:
        if not is_pseudo_already_used(pseudo_candidate, user_id):
            payload["pseudo"] = pseudo_candidate
    except HTTPException:
        pass

    try:
        supabase_admin.table("users").insert(payload).execute()
    except APIError:
        pass

    return get_user_row_by_id(user_id)


def sync_profile_if_needed(
    user_row: dict,
    user_id: str,
    email: str | None,
    metadata: dict[str, Any],
) -> dict:
    """Backfill missing profile fields from auth metadata when needed.
    
    Args:
        user_row (dict): Parameter user_row.
        user_id (str): User identifier.
        email (str | None): Parameter email.
        metadata (dict[str, Any]): Parameter metadata.
    
    Returns:
        dict: Result of the operation.
    """
    update_payload: dict[str, Any] = {}

    if email and user_row.get("email") != email:
        update_payload["email"] = email

    avatar_from_auth = metadata.get("avatar_url") or metadata.get("picture")
    if isinstance(avatar_from_auth, str) and avatar_from_auth.strip() and not user_row.get("avatar_url"):
        update_payload["avatar_url"] = avatar_from_auth.strip()

    cover_from_auth = metadata.get("cover_url")
    if isinstance(cover_from_auth, str) and cover_from_auth.strip() and not user_row.get("cover_url"):
        update_payload["cover_url"] = cover_from_auth.strip()

    if not user_row.get("pseudo"):
        candidate = build_fallback_pseudo(user_id, email, metadata)
        try:
            if not is_pseudo_already_used(candidate, user_id):
                update_payload["pseudo"] = candidate
        except HTTPException:
            pass

    if not update_payload:
        return user_row

    try:
        supabase_admin.table("users").update(update_payload).eq("id", user_id).execute()
    except APIError as exc:
        message = str(exc).lower()
        if "duplicate" in message and "pseudo" in message and "pseudo" in update_payload:
            update_payload.pop("pseudo", None)
            if update_payload:
                try:
                    supabase_admin.table("users").update(update_payload).eq("id", user_id).execute()
                except APIError:
                    return user_row
            else:
                return user_row
        else:
            return user_row

    return get_user_row_by_id(user_id) or user_row


def is_pseudo_already_used(pseudo: str, current_user_id: str) -> bool:
    """Check whether pseudo is already used by another user.
    
    Args:
        pseudo (str): Parameter pseudo.
        current_user_id (str): Identifier for current user.
    
    Returns:
        bool: True if pseudo already used, otherwise False.
    """
    try:
        result = (
            supabase_admin.table("users")
            .select("id")
            .eq("pseudo", pseudo)
            .neq("id", current_user_id)
            .limit(1)
            .execute()
        )
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"Pseudo lookup failed: {exc}") from exc

    return bool(result.data)
