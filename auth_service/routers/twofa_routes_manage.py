"""2FA enable/verify/disable routes."""

import base64
import io

import pyotp
import qrcode
from fastapi import APIRouter, Header, HTTPException
from postgrest.exceptions import APIError

from core.twofa_context import FLAG_COLUMNS, SECRET_COLUMNS, supabase_admin
from utils.twofa_helpers import extract_totp_secret, is_missing_column_error, resolve_user_id
from stores.twofa_storage import (
    get_secret_from_metadata,
    safe_update_user_columns,
    update_auth_user_metadata,
)
from schemas.models import Verify2FAForm

twofa_manage_router = APIRouter()


@twofa_manage_router.post(
    "/enable",
    summary="Enable 2FA for user",
    description="Generate TOTP secret and QR code for user to enable 2FA.",
)
def enable_2fa(
    x_user_id: str = Header(None),
    x_access_token: str = Header(None),
    x_user_email: str = Header(None),
):
    """Initialize TOTP secret and return QR payload.
    
    Args:
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
        x_user_email (str): Parameter x_user_email.
    
    Returns:
        Any: Result of the operation.
    """
    resolved_user_id = resolve_user_id(x_user_id, x_access_token)
    if not resolved_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: missing or invalid access token")

    secret = pyotp.random_base32()
    account_name = (x_user_email or "").strip() or resolved_user_id
    issuer_name = "peerloop"
    uri = pyotp.TOTP(secret).provisioning_uri(name=account_name, issuer_name=issuer_name)
    image = qrcode.make(uri)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    payload = {
        "qr_code": qr_base64,
        "otpauth_url": uri,
        "secret": secret,
        "account_name": account_name,
        "issuer": issuer_name,
        "message": "Scan QR and verify",
    }

    try:
        updated = (
            supabase_admin.table("users")
            .update({"totp_secret": secret, "totp_enabled": False})
            .eq("id", resolved_user_id)
            .execute()
        )
        if not updated.data:
            raise HTTPException(status_code=404, detail="User profile not found")
        update_auth_user_metadata(
            resolved_user_id,
            {"totp_secret": secret, "totp_enabled": False, "is_2fa_enabled": False},
        )
        return payload
    except APIError as exc:
        if is_missing_column_error(exc, "totp_enabled"):
            try:
                updated = (
                    supabase_admin.table("users")
                    .update({"totp_secret": secret})
                    .eq("id", resolved_user_id)
                    .execute()
                )
                if not updated.data:
                    raise HTTPException(status_code=404, detail="User profile not found")
                update_auth_user_metadata(
                    resolved_user_id,
                    {"totp_secret": secret, "totp_enabled": False, "is_2fa_enabled": False},
                )
                return payload
            except APIError as fallback_exc:
                if is_missing_column_error(fallback_exc, "totp_secret"):
                    update_auth_user_metadata(
                        resolved_user_id,
                        {"totp_secret": secret, "totp_enabled": False, "is_2fa_enabled": False},
                    )
                    return payload
                raise HTTPException(
                    status_code=502,
                    detail=f"2FA storage update failed: {fallback_exc}",
                ) from fallback_exc

        if is_missing_column_error(exc, "totp_secret"):
            update_auth_user_metadata(
                resolved_user_id,
                {"totp_secret": secret, "totp_enabled": False, "is_2fa_enabled": False},
            )
            return payload

        raise HTTPException(status_code=502, detail=f"2FA storage update failed: {exc}") from exc


@twofa_manage_router.post(
    "/verify",
    summary="Verify 2FA code",
    description="Verify the TOTP code sent by the user and activate 2FA.",
)
def verify_2fa(form: Verify2FAForm, x_user_id: str = Header(None), x_access_token: str = Header(None)):
    """Validate TOTP code and enable 2FA flags.
    
    Args:
        form (Verify2FAForm): Parameter form.
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: TOTP code and enable 2FA flags.
    """
    resolved_user_id = resolve_user_id(x_user_id, x_access_token)
    if not resolved_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: missing or invalid access token")

    try:
        user = supabase_admin.table("users").select("*").eq("id", resolved_user_id).single().execute().data
    except APIError:
        user = None

    secret = extract_totp_secret(user or {}) or get_secret_from_metadata(resolved_user_id)
    if not secret:
        raise HTTPException(status_code=404, detail="2FA not initialized")

    if not pyotp.TOTP(secret).verify(form.code):
        raise HTTPException(status_code=401, detail="Invalid 2FA code")

    for flag_column in FLAG_COLUMNS:
        try:
            supabase_admin.table("users").update({flag_column: True}).eq("id", resolved_user_id).execute()
            break
        except APIError as exc:
            if is_missing_column_error(exc, flag_column):
                continue
            raise HTTPException(status_code=502, detail=f"2FA verification update failed: {exc}") from exc

    update_auth_user_metadata(
        resolved_user_id,
        {"totp_enabled": True, "is_2fa_enabled": True, "totp_secret": secret},
    )
    return {"message": "2FA enabled"}


@twofa_manage_router.post(
    "/disable",
    summary="Disable 2FA",
    description="Disable 2FA for user and clear stored TOTP secret.",
)
def disable_2fa(x_user_id: str = Header(None), x_access_token: str = Header(None)):
    """Disable 2FA and clear secrets/flags from storage and metadata.
    
    Args:
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Result of the operation.
    """
    resolved_user_id = resolve_user_id(x_user_id, x_access_token)
    if not resolved_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: missing or invalid access token")

    updates = {column: None for column in SECRET_COLUMNS}
    updates.update({column: False for column in FLAG_COLUMNS})
    safe_update_user_columns(resolved_user_id, updates)
    update_auth_user_metadata(
        resolved_user_id,
        {
            "totp_secret": None,
            "twofa_secret": None,
            "otp_secret": None,
            "totp_enabled": False,
            "twofa_enabled": False,
            "is_2fa_enabled": False,
        },
    )
    return {"message": "2FA disabled"}
