"""Profile synchronization and serialization helpers."""

from typing import Any

from core.user_context import supabase
from stores.user_identity import build_fallback_pseudo, select_user_profile_by_id


def sync_user_profile_row(
    user_id: str,
    email: str | None,
    user_metadata: dict[str, Any],
) -> dict[str, Any] | None:
    """Create/update profile row with metadata-enriched defaults.
    
    Args:
        user_id (str): User identifier.
        email (str | None): Parameter email.
        user_metadata (dict[str, Any]): Parameter user_metadata.
    
    Returns:
        dict[str, Any] | None: Result of the operation.
    """
    avatar_url = user_metadata.get("avatar_url") or user_metadata.get("picture")
    cover_url = user_metadata.get("cover_url")
    pseudo = build_fallback_pseudo(email, user_metadata)

    current_row = select_user_profile_by_id(user_id)
    if not current_row:
        insert_payload: dict[str, Any] = {"id": user_id, "email": email}
        if isinstance(avatar_url, str) and avatar_url.strip():
            insert_payload["avatar_url"] = avatar_url.strip()
        if isinstance(cover_url, str) and cover_url.strip():
            insert_payload["cover_url"] = cover_url.strip()
        try:
            supabase.table("users").insert(insert_payload).execute()
        except Exception:
            pass
        current_row = select_user_profile_by_id(user_id)
        if not current_row:
            return None

    update_payload: dict[str, Any] = {}
    current_email = current_row.get("email")
    if email and current_email != email:
        update_payload["email"] = email

    if isinstance(avatar_url, str) and avatar_url.strip() and not current_row.get("avatar_url"):
        update_payload["avatar_url"] = avatar_url.strip()

    if isinstance(cover_url, str) and cover_url.strip() and not current_row.get("cover_url"):
        update_payload["cover_url"] = cover_url.strip()

    if pseudo and not current_row.get("pseudo"):
        update_payload["pseudo"] = pseudo

    if update_payload:
        try:
            supabase.table("users").update(update_payload).eq("id", user_id).execute()
        except Exception as exc:
            if "duplicate key value violates unique constraint" in str(exc).lower() and "pseudo" in update_payload:
                update_payload.pop("pseudo", None)
                if update_payload:
                    try:
                        supabase.table("users").update(update_payload).eq("id", user_id).execute()
                    except Exception:
                        pass

    return select_user_profile_by_id(user_id)


def build_profile_payload(
    user_row: dict[str, Any] | None,
    user_id: str,
    email: str | None,
) -> dict[str, Any]:
    """Serialize full profile payload with safe fallback values.
    
    Args:
        user_row (dict[str, Any] | None): Parameter user_row.
        user_id (str): User identifier.
        email (str | None): Parameter email.
    
    Returns:
        dict[str, Any]: Full profile payload with safe fallback values.
    """
    if user_row:
        return {
            "id": user_row.get("id") or user_id,
            "pseudo": user_row.get("pseudo"),
            "email": user_row.get("email") or email,
            "address": user_row.get("address"),
            "bio": user_row.get("bio"),
            "avatar_id": user_row.get("avatar_id"),
            "avatar_url": user_row.get("avatar_url"),
            "cover_id": user_row.get("cover_id"),
            "cover_url": user_row.get("cover_url"),
            "created_at": user_row.get("created_at"),
            "updated_at": user_row.get("updated_at"),
        }

    fallback_pseudo = build_fallback_pseudo(email, {})
    return {
        "id": user_id,
        "pseudo": fallback_pseudo,
        "email": email,
        "address": None,
        "bio": None,
        "avatar_id": None,
        "avatar_url": None,
        "cover_id": None,
        "cover_url": None,
        "created_at": None,
        "updated_at": None,
    }
