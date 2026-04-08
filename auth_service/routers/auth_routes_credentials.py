"""Credential/session endpoints for auth service."""

import pyotp
import httpx
from fastapi import APIRouter, Cookie, HTTPException, Response
from fastapi.responses import JSONResponse
from gotrue.errors import AuthApiError

from core.auth_context import (
    EMAIL_CONFIRM_REDIRECT_URL,
    REFRESH_TOKEN_COOKIE_NAME,
    Login2FAVerifyRequest,
    RefreshRequest,
    SessionExchangeRequest,
    new_supabase_client,
    supabase,
)
from stores.auth_identity_lookup import get_auth_user_metadata_by_id, get_user_by_id
from services.auth_pending_challenges import (
    create_pending_login_2fa_challenge,
    delete_pending_login_2fa_challenge,
    get_pending_login_2fa_challenge,
)
from services.auth_profile_utils import ensure_user_profile
from services.auth_session_utils import (
    clear_refresh_cookie,
    extract_auth_user,
    extract_session,
    session_value,
    set_refresh_cookie,
)
from utils.auth_token_utils import extract_auth_metadata, extract_totp_secret, is_2fa_enabled
from shared_schemas.models import LoginRequest, SignupRequest

auth_credentials_router = APIRouter()


@auth_credentials_router.post("/register", status_code=201)
def register(payload: SignupRequest) -> dict[str, str]:
    """Register user in Supabase auth and provision users table row.
    
    Args:
        payload (SignupRequest): Parsed request payload.
    
    Returns:
        dict[str, str]: Result of the operation.
    """
    email = payload.email
    username = payload.username
    password = payload.password

    try:
        existing_email = supabase.table("users").select("id").eq("email", email).execute()
        if existing_email.data:
            raise HTTPException(status_code=409, detail="Email already in use")
    except HTTPException:
        raise
    except Exception:
        existing_email = None

    try:
        existing_pseudo = supabase.table("users").select("id").eq("pseudo", username).execute()
        if existing_pseudo.data:
            raise HTTPException(status_code=409, detail="Username already in use")
    except HTTPException:
        raise
    except Exception:
        existing_pseudo = None

    def _extract_user_id(auth_response):
        """Extract a user id from a Supabase auth response payload.
        
        Args:
            auth_response (Any): Parameter auth_response.
        
        Returns:
            Any: User id from a Supabase auth response payload.
        """
        if auth_response is None:
            return None, None
        if isinstance(auth_response, dict):
            for key in ("user", "data"):
                value = auth_response.get(key)
                if isinstance(value, dict) and value.get("id"):
                    return value.get("id"), auth_response
            if auth_response.get("id"):
                return auth_response.get("id"), auth_response
            return None, auth_response.get("error") or auth_response.get("message") or auth_response

        user = getattr(auth_response, "user", None)
        if user:
            if isinstance(user, dict):
                return user.get("id"), auth_response
            if hasattr(user, "id"):
                return getattr(user, "id"), auth_response

        data = getattr(auth_response, "data", None)
        if isinstance(data, dict):
            if data.get("id"):
                return data.get("id"), auth_response
            if isinstance(data.get("user"), dict) and data["user"].get("id"):
                return data["user"].get("id"), auth_response

        error_value = None
        try:
            if isinstance(auth_response, dict):
                error_value = auth_response.get("error") or auth_response.get("message")
        except Exception:
            error_value = None
        return None, error_value

    def _is_email_conflict(error_value) -> bool:
        """Tell whether an error indicates a duplicated email address.
        
        Args:
            error_value (Any): Parameter error_value.
        
        Returns:
            bool: True if email conflict, otherwise False.
        """
        if not error_value:
            return False
        message = str(error_value).lower()
        return (
            "already registered" in message
            or ("already" in message and "exists" in message)
            or "email address not authorized" in message
            or "email already" in message
        )

    user_id = None
    last_error = None
    try:
        auth_response = supabase.auth.sign_up(
            {
                "email": email,
                "password": password,
                "options": {
                    "data": {"username": username},
                    "email_redirect_to": EMAIL_CONFIRM_REDIRECT_URL,
                },
            }
        )
        user_id, last_error = _extract_user_id(auth_response)
    except Exception as exc:
        last_error = str(exc)
        try:
            auth_response = supabase.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                    "options": {"email_redirect_to": EMAIL_CONFIRM_REDIRECT_URL},
                }
            )
            user_id, extra_error = _extract_user_id(auth_response)
            if not last_error and extra_error:
                last_error = extra_error
        except Exception as fallback_exc:
            last_error = last_error or str(fallback_exc)

    if not user_id:
        if _is_email_conflict(last_error):
            raise HTTPException(status_code=409, detail="Email already in use")
        if last_error and "signups not allowed" in str(last_error).lower():
            raise HTTPException(status_code=403, detail="Signup is disabled in Supabase Auth settings")
        detail = f"Signup failed: {last_error}" if last_error else "Signup failed"
        raise HTTPException(status_code=502, detail=detail)

    try:
        supabase.table("users").insert({"id": user_id, "email": email, "pseudo": username}).execute()
    except Exception:
        pass

    return {
        "message": "User registered successfully. Please check your email to confirm your account.",
        "user_id": str(user_id),
    }


@auth_credentials_router.post(
    "/login",
    summary="Login with email and password",
    description="Authenticate a user with email and password. Returns access token or 2FA requirement.",
)
def login(payload: LoginRequest, response: Response):
    """Authenticate user and issue tokens or pending 2FA challenge.
    
    Args:
        payload (LoginRequest): Parsed request payload.
        response (Response): FastAPI response object to mutate.
    
    Returns:
        Any: Result of the operation.
    """
    identifier = payload.email.strip()
    if not identifier:
        raise HTTPException(status_code=422, detail="Email or username is required")

    login_email = identifier
    if "@" not in identifier:
        try:
            user_lookup = (
                supabase.table("users")
                .select("email")
                .eq("pseudo", identifier)
                .limit(1)
                .execute()
            )
            lookup_rows = user_lookup.data or []
            if lookup_rows and lookup_rows[0].get("email"):
                login_email = str(lookup_rows[0]["email"])
            else:
                raise HTTPException(status_code=401, detail="Invalid credentials")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=401, detail="Invalid credentials") from exc

    auth_client = new_supabase_client()
    try:
        auth = auth_client.auth.sign_in_with_password({"email": login_email, "password": payload.password})
    except (AuthApiError, httpx.HTTPStatusError) as exc:
        message = getattr(exc, "message", None) or str(exc)
        raise HTTPException(status_code=401, detail=f"Invalid credentials: {message}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Auth provider error: {str(exc)}") from exc

    session = extract_session(auth)
    user_obj = auth.get("user") if isinstance(auth, dict) else getattr(auth, "user", None)
    if isinstance(auth, dict) and not user_obj:
        user_obj = (auth.get("data") or {}).get("user")

    if not session:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    try:
        user = supabase.table("users").select("*").eq("email", login_email).single().execute().data
    except Exception:
        user = None

    if is_2fa_enabled(user, user_obj):
        user_id = None
        if isinstance(user, dict):
            user_id = user.get("id")
        if not user_id and isinstance(user_obj, dict):
            user_id = user_obj.get("id")
        if not user_id and user_obj is not None:
            user_id = getattr(user_obj, "id", None)

        access_token = session_value(session, "access_token")
        refresh_token = session_value(session, "refresh_token")
        if not user_id or not access_token:
            raise HTTPException(status_code=502, detail="Unable to initialize 2FA login challenge")

        challenge_id = create_pending_login_2fa_challenge(
            user_id=str(user_id),
            access_token=str(access_token),
            refresh_token=refresh_token,
        )
        return JSONResponse(
            status_code=202,
            content={"2fa_required": True, "user_id": user_id, "challenge_id": challenge_id},
        )

    access_token = session_value(session, "access_token")
    refresh_token = session_value(session, "refresh_token")
    if not access_token:
        raise HTTPException(status_code=502, detail="Failed to obtain access token")

    if refresh_token:
        set_refresh_cookie(response, refresh_token)

    response.headers["Authorization"] = f"Bearer {access_token}"
    return {"access_token": access_token, "token_type": "bearer"}


@auth_credentials_router.post(
    "/login/2fa/verify",
    summary="Finalize login with 2FA",
    description="Validate a pending login 2FA challenge and issue access token + refresh cookie.",
)
def verify_login_2fa(payload: Login2FAVerifyRequest, response: Response):
    """Verify pending challenge against stored TOTP secret and issue tokens.
    
    Args:
        payload (Login2FAVerifyRequest): Parsed request payload.
        response (Response): FastAPI response object to mutate.
    
    Returns:
        Any: Result of the operation.
    """
    challenge_id = (payload.challenge_id or "").strip()
    if not challenge_id:
        raise HTTPException(status_code=422, detail="Missing 2FA challenge id")

    challenge = get_pending_login_2fa_challenge(challenge_id)
    if not challenge:
        raise HTTPException(status_code=401, detail="2FA challenge expired or invalid")

    normalized_code = (payload.code or "").strip().replace(" ", "")
    if not normalized_code.isdigit() or len(normalized_code) != 6:
        raise HTTPException(status_code=422, detail="Invalid 2FA code format")

    user_id = str(challenge.get("user_id") or "").strip()
    if not user_id:
        delete_pending_login_2fa_challenge(challenge_id)
        raise HTTPException(status_code=401, detail="Invalid 2FA challenge payload")

    user = get_user_by_id(user_id)
    metadata = get_auth_user_metadata_by_id(user_id)
    secret = extract_totp_secret(user) or extract_totp_secret(metadata)
    if not secret:
        delete_pending_login_2fa_challenge(challenge_id)
        raise HTTPException(status_code=401, detail="2FA is not initialized for this account")

    if not pyotp.TOTP(secret).verify(normalized_code):
        raise HTTPException(status_code=401, detail="Invalid 2FA code")

    access_token = str(challenge.get("access_token") or "").strip()
    refresh_token = str(challenge.get("refresh_token") or "").strip()
    if not access_token:
        delete_pending_login_2fa_challenge(challenge_id)
        raise HTTPException(status_code=401, detail="Missing access token in 2FA challenge")

    if refresh_token:
        set_refresh_cookie(response, refresh_token)

    response.headers["Authorization"] = f"Bearer {access_token}"
    delete_pending_login_2fa_challenge(challenge_id)
    return {"access_token": access_token, "token_type": "bearer"}


@auth_credentials_router.post(
    "/session/exchange",
    summary="Accept browser callback session",
    description="Accept access/refresh tokens from frontend callback, validate session and store refresh token in HttpOnly cookie.",
)
def session_exchange(payload: SessionExchangeRequest, response: Response):
    """Validate callback session and synchronize user profile row.
    
    Args:
        payload (SessionExchangeRequest): Parsed request payload.
        response (Response): FastAPI response object to mutate.
    
    Returns:
        Any: Callback session and synchronize user profile row.
    """
    auth_client = new_supabase_client()
    try:
        auth = auth_client.auth.set_session(payload.access_token, payload.refresh_token)
    except (AuthApiError, httpx.HTTPStatusError) as exc:
        clear_refresh_cookie(response)
        message = getattr(exc, "message", None) or str(exc)
        raise HTTPException(status_code=401, detail=f"Invalid session payload: {message}") from exc
    except Exception as exc:
        clear_refresh_cookie(response)
        raise HTTPException(status_code=502, detail=f"Auth provider error: {str(exc)}") from exc

    session = extract_session(auth)
    auth_user = extract_auth_user(auth)
    auth_metadata = extract_auth_metadata(auth_user)
    access_token = session_value(session, "access_token") or payload.access_token
    refresh_token = session_value(session, "refresh_token") or payload.refresh_token

    if not access_token:
        clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Session exchange failed: missing access token")
    if not refresh_token:
        clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Session exchange failed: missing refresh token")

    auth_user_id = auth_user.get("id") if isinstance(auth_user, dict) else getattr(auth_user, "id", None)
    auth_user_email = auth_user.get("email") if isinstance(auth_user, dict) else getattr(auth_user, "email", None)
    if not auth_user_id or not auth_user_email:
        clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Session exchange failed: missing authenticated user data")

    display_name = (
        auth_metadata.get("full_name")
        or auth_metadata.get("name")
        or auth_metadata.get("username")
        or auth_user_email
    )
    avatar_url = auth_metadata.get("avatar_url") or auth_metadata.get("picture")
    ensure_user_profile(
        auth_user_id=str(auth_user_id),
        email=str(auth_user_email),
        pseudo_seed=display_name,
        avatar_url=avatar_url,
    )

    set_refresh_cookie(response, refresh_token)
    response.headers["Authorization"] = f"Bearer {access_token}"
    return {"access_token": access_token, "token_type": "bearer"}


@auth_credentials_router.post(
    "/refresh",
    summary="Refresh access token",
    description="Issue a new access token using refresh token from HttpOnly cookie (or explicit body fallback).",
)
def refresh_access_token(
    response: Response,
    payload: RefreshRequest | None = None,
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_TOKEN_COOKIE_NAME),
):
    """Refresh access token from cookie/body refresh token.
    
    Args:
        response (Response): FastAPI response object to mutate.
        payload (RefreshRequest | None): Parsed request payload.
        refresh_cookie (str | None): Parameter refresh_cookie.
    
    Returns:
        Any: Result of the operation.
    """
    refresh_token = (payload.refresh_token if payload and payload.refresh_token else refresh_cookie) or ""
    refresh_token = refresh_token.strip()
    if not refresh_token:
        clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Missing refresh token")

    auth_client = new_supabase_client()
    try:
        auth = auth_client.auth.refresh_session(refresh_token)
    except (AuthApiError, httpx.HTTPStatusError) as exc:
        clear_refresh_cookie(response)
        message = getattr(exc, "message", None) or str(exc)
        raise HTTPException(status_code=401, detail=f"Refresh failed: {message}") from exc
    except Exception as exc:
        clear_refresh_cookie(response)
        raise HTTPException(status_code=502, detail=f"Auth provider error: {str(exc)}") from exc

    session = extract_session(auth)
    new_access_token = session_value(session, "access_token")
    new_refresh_token = session_value(session, "refresh_token") or refresh_token
    if not new_access_token:
        clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Refresh failed: missing access token")

    set_refresh_cookie(response, new_refresh_token)
    response.headers["Authorization"] = f"Bearer {new_access_token}"
    return {"access_token": new_access_token, "token_type": "bearer"}
