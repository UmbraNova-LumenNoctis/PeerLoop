"""2FA status route."""

from fastapi import APIRouter, Header, HTTPException

from utils.twofa_helpers import extract_totp_secret, resolve_twofa_enabled, resolve_user_id
from stores.twofa_storage import get_auth_user_metadata, load_user_profile

twofa_status_router = APIRouter()


@twofa_status_router.get(
    "/status",
    summary="Get 2FA status",
    description="Returns whether 2FA is initialized and enabled for the user.",
)
def get_2fa_status(x_user_id: str = Header(None), x_access_token: str = Header(None)):
    """Return current 2FA activation state for authenticated user.
    
    Args:
        x_user_id (str): Identifier for x user.
        x_access_token (str): Parameter x_access_token.
    
    Returns:
        Any: Current 2FA activation state for authenticated user.
    """
    resolved_user_id = resolve_user_id(x_user_id, x_access_token)
    if not resolved_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: missing or invalid access token")

    user = load_user_profile(resolved_user_id)
    metadata = get_auth_user_metadata(resolved_user_id)
    initialized = bool(extract_totp_secret(user) or extract_totp_secret(metadata))
    enabled = resolve_twofa_enabled(user, metadata)
    return {"enabled": enabled, "initialized": initialized}
