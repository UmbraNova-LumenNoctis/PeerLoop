"""User profile synchronization helpers for auth flows."""

import re
import uuid

from fastapi import HTTPException
from postgrest.exceptions import APIError

from core.auth_context import AUTH_STRICT_EMAIL_LINKING, supabase
from utils.auth_token_utils import normalized_email


def sanitize_pseudo(raw_value: str | None, email: str) -> str:
    """Normalize pseudo candidate to a safe username.
    
    Args:
        raw_value (str | None): Parameter raw_value.
        email (str): Parameter email.
    
    Returns:
        str: Pseudo candidate to a safe username.
    """
    candidate = (raw_value or "").strip() or email.split("@")[0]
    candidate = re.sub(r"\s+", "_", candidate)
    candidate = re.sub(r"[^A-Za-z0-9_.-]", "", candidate)
    candidate = candidate.strip("._-")

    if not candidate:
        candidate = "user"
    if len(candidate) < 3:
        candidate = f"{candidate}_{uuid.uuid4().hex[:4]}"
    return candidate[:30]


def is_pseudo_taken(pseudo: str) -> bool:
    """Tell whether pseudo already exists in ``users`` table.
    
    Args:
        pseudo (str): Parameter pseudo.
    
    Returns:
        bool: True if pseudo taken, otherwise False.
    """
    try:
        result = (
            supabase.table("users")
            .select("id")
            .eq("pseudo", pseudo)
            .limit(1)
            .execute()
        )
    except Exception:
        return False
    return bool(result.data)


def build_unique_pseudo(preferred_value: str | None, email: str) -> str:
    """Generate a unique pseudo using suffix retries when needed.
    
    Args:
        preferred_value (str | None): Parameter preferred_value.
        email (str): Parameter email.
    
    Returns:
        str: Constructed value.
    """
    base = sanitize_pseudo(preferred_value, email)
    if not is_pseudo_taken(base):
        return base

    for _ in range(12):
        suffix = f"_{uuid.uuid4().hex[:6]}"
        candidate = f"{base[:30 - len(suffix)]}{suffix}"
        if not is_pseudo_taken(candidate):
            return candidate

    return f"user_{uuid.uuid4().hex[:8]}"[:30]


def get_user_by_email(email: str) -> dict | None:
    """Fetch first user row by email with case-insensitive fallback.
    
    Args:
        email (str): Parameter email.
    
    Returns:
        dict | None: First user row by email with case-insensitive fallback.
    """
    normalized = normalized_email(email)
    if not normalized:
        return None

    try:
        rows = (
            supabase.table("users")
            .select("*")
            .ilike("email", normalized)
            .limit(1)
            .execute()
            .data
            or []
        )
        if rows:
            return rows[0]
    except Exception:
        pass

    try:
        rows = (
            supabase.table("users")
            .select("*")
            .eq("email", normalized)
            .limit(1)
            .execute()
            .data
            or []
        )
        return rows[0] if rows else None
    except Exception:
        return None


def ensure_user_profile(
    auth_user_id: str,
    email: str,
    pseudo_seed: str | None,
    avatar_url: str | None = None,
) -> dict:
    """Create or synchronize a row in ``users`` for authenticated account.
    
    Args:
        auth_user_id (str): Identifier for auth user.
        email (str): Parameter email.
        pseudo_seed (str | None): Parameter pseudo_seed.
        avatar_url (str | None): URL for avatar.
    
    Returns:
        dict: Or synchronize a row in ``users`` for authenticated account.
    """
    normalized = normalized_email(email)
    if not auth_user_id:
        raise HTTPException(status_code=401, detail="User id is missing")
    if not normalized:
        raise HTTPException(status_code=401, detail="User email is missing")

    existing_by_id = None
    try:
        rows = (
            supabase.table("users")
            .select("*")
            .eq("id", auth_user_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        existing_by_id = rows[0] if rows else None
    except Exception:
        existing_by_id = None

    existing_by_email = get_user_by_email(normalized)
    if (
        AUTH_STRICT_EMAIL_LINKING
        and existing_by_email
        and str(existing_by_email.get("id") or "") != str(auth_user_id)
    ):
        raise HTTPException(
            status_code=409,
            detail="This email is already linked to another account. Use that account instead.",
        )

    user = existing_by_id or (
        existing_by_email
        if existing_by_email and str(existing_by_email.get("id") or "") == str(auth_user_id)
        else None
    )

    if not user:
        user_payload = {
            "id": auth_user_id,
            "email": normalized,
            "pseudo": build_unique_pseudo(pseudo_seed, normalized),
            "avatar_url": avatar_url,
        }
        for _ in range(5):
            try:
                created = supabase.table("users").insert(user_payload).execute()
                created_rows = created.data or []
                user = created_rows[0] if created_rows else user_payload
                break
            except APIError as exc:
                detail = str(exc).lower()
                if "duplicate key value violates unique constraint" in detail and "pseudo" in detail:
                    user_payload["pseudo"] = build_unique_pseudo(pseudo_seed, normalized)
                    continue
                if "duplicate key value violates unique constraint" in detail and "users_pkey" in detail:
                    existing_rows = (
                        supabase.table("users")
                        .select("*")
                        .eq("id", auth_user_id)
                        .limit(1)
                        .execute()
                        .data
                        or []
                    )
                    user = existing_rows[0] if existing_rows else None
                    break
                raise HTTPException(status_code=502, detail=f"User profile provisioning failed: {exc}")

        if not user:
            raise HTTPException(status_code=502, detail="User profile provisioning failed")
    else:
        update_payload: dict[str, str] = {}
        if normalized and normalized_email(user.get("email")) != normalized:
            update_payload["email"] = normalized
        if avatar_url and not user.get("avatar_url"):
            update_payload["avatar_url"] = avatar_url
        if not user.get("pseudo"):
            update_payload["pseudo"] = build_unique_pseudo(pseudo_seed, normalized)

        if update_payload:
            try:
                updated = (
                    supabase.table("users")
                    .update(update_payload)
                    .eq("id", auth_user_id)
                    .execute()
                )
                updated_rows = updated.data or []
                if updated_rows:
                    user = updated_rows[0]
            except APIError:
                pass

    return dict(user or {})
