"""Google OAuth and callback endpoints for auth service."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from core.auth_context import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REQUIRE_VERIFIED_EMAIL,
    POST_CONFIRM_APP_URL,
    SUPABASE_KEY,
    SUPABASE_URL,
)
from utils.auth_google_config import (
    ensure_google_oauth_configured,
    is_google_direct_oauth_configured,
    parse_google_redirect_candidates,
    resolve_google_redirect_uri,
)
from services.auth_google_flow import (
    build_frontend_login_redirect,
    build_supabase_google_authorize_url,
    should_use_supabase_fallback,
)
from services.auth_profile_utils import ensure_user_profile
from services.auth_session_utils import set_refresh_cookie
from utils.auth_token_utils import coerce_bool, normalized_email

auth_google_router = APIRouter()



@auth_google_router.get(
    "/email/confirm",
    summary="Email confirmation callback",
    description="Receives Supabase email confirmation redirect and forwards the user to the app.",
)
def email_confirm_callback():
    """Redirect user to frontend with confirmation query flag.
    
    Returns:
        Any: Result of the operation.
    """
    app_url = (POST_CONFIRM_APP_URL or "https://localhost:8443").strip() or "https://localhost:8443"
    parts = urlsplit(app_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["confirmed"] = "1"
    target_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query, doseq=True), ""))
    return RedirectResponse(url=target_url, status_code=307)


@auth_google_router.get(
    "/login/google",
    summary="Google OAuth login URL",
    description="Get the Google OAuth login URL to redirect the user for authentication.",
)
def login_google():
    """Return Google OAuth URL in direct mode or Supabase fallback mode.
    
    Returns:
        Any: Google OAuth URL in direct mode or Supabase fallback mode.
    """
    if not is_google_direct_oauth_configured():
        if should_use_supabase_fallback():
            return {"url": build_supabase_google_authorize_url(), "mode": "supabase_fallback"}
        raise HTTPException(
            status_code=503,
            detail="Google OAuth direct mode is not configured (set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, REDIRECT_URI).",
        )

    ensure_google_oauth_configured()
    redirect_uri = resolve_google_redirect_uri()
    query = urlencode(
        {
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
        }
    )
    return {
        "url": f"https://accounts.google.com/o/oauth2/v2/auth?{query}",
        "mode": "google_direct",
        "redirect_uri": redirect_uri,
        "redirect_uri_candidates": parse_google_redirect_candidates(),
    }


@auth_google_router.get(
    "/google/callback",
    summary="Handle Google OAuth callback",
    description="Exchange authorization code for access token and create/fetch user.",
)
def auth_google(code: str | None = None, error: str | None = None):
    """Handle Google callback, create Supabase session, and redirect frontend.
    
    Args:
        code (str | None): Parameter code.
        error (str | None): Parameter error.
    
    Returns:
        Any: Result of the operation.
    """
    if not is_google_direct_oauth_configured():
        if not should_use_supabase_fallback():
            raise HTTPException(
                status_code=503,
                detail="Google OAuth direct mode is not configured (set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, REDIRECT_URI).",
            )
        return RedirectResponse(
            url=build_frontend_login_redirect(
                error="Google callback is unavailable in fallback mode. Start login again from /api/auth/google."
            ),
            status_code=307,
        )

    ensure_google_oauth_configured()
    redirect_uri = resolve_google_redirect_uri()
    if error:
        return RedirectResponse(url=build_frontend_login_redirect(error=f"Google OAuth failed: {error}"), status_code=307)
    if not code or len(code) < 10:
        return RedirectResponse(
            url=build_frontend_login_redirect(error="Google OAuth failed: invalid authorization code"),
            status_code=307,
        )

    try:
        token_resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
            timeout=10,
        )
        token_resp.raise_for_status()
        token_res = token_resp.json()
    except requests.RequestException as exc:
        return RedirectResponse(
            url=build_frontend_login_redirect(error=f"Google token exchange failed: {exc}"),
            status_code=307,
        )

    access_token = token_res.get("access_token")
    id_token = token_res.get("id_token")
    if not access_token:
        return RedirectResponse(
            url=build_frontend_login_redirect(error="Google OAuth failed: missing access token"),
            status_code=307,
        )
    if not id_token:
        return RedirectResponse(
            url=build_frontend_login_redirect(error="Google OAuth failed: missing id token"),
            status_code=307,
        )

    try:
        userinfo_resp = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        userinfo_resp.raise_for_status()
        userinfo = userinfo_resp.json()
    except requests.RequestException as exc:
        return RedirectResponse(
            url=build_frontend_login_redirect(error=f"Google user info request failed: {exc}"),
            status_code=307,
        )

    email = userinfo.get("email")
    email_verified = coerce_bool(userinfo.get("email_verified"))
    if not email:
        return RedirectResponse(
            url=build_frontend_login_redirect(error="Google OAuth failed: email not returned by Google"),
            status_code=307,
        )
    if GOOGLE_REQUIRE_VERIFIED_EMAIL and email_verified is not True:
        return RedirectResponse(
            url=build_frontend_login_redirect(error="Google OAuth failed: email is not verified"),
            status_code=307,
        )

    pseudo_seed = userinfo.get("given_name") or email.split("@")[0]
    google_avatar_url = userinfo.get("picture") or userinfo.get("avatar_url")

    try:
        session_resp = requests.post(
            f"{SUPABASE_URL.rstrip('/')}/auth/v1/token?grant_type=id_token",
            json={
                "provider": "google",
                "id_token": id_token,
                "access_token": access_token,
            },
            headers={"apikey": SUPABASE_KEY, "Content-Type": "application/json"},
            timeout=10,
        )
        session_resp.raise_for_status()
        session_payload = session_resp.json()
    except requests.RequestException as exc:
        return RedirectResponse(
            url=build_frontend_login_redirect(error=f"Supabase session exchange failed: {exc}"),
            status_code=307,
        )

    app_access_token = session_payload.get("access_token")
    app_refresh_token = session_payload.get("refresh_token")
    session_user = session_payload.get("user") or {}

    auth_user_id = session_user.get("id")
    session_email = normalized_email(session_user.get("email"))
    if session_email and session_email != normalized_email(email):
        return RedirectResponse(
            url=build_frontend_login_redirect(error="Google OAuth failed: session email mismatch"),
            status_code=307,
        )
    if GOOGLE_REQUIRE_VERIFIED_EMAIL and not session_user.get("email_confirmed_at"):
        return RedirectResponse(
            url=build_frontend_login_redirect(error="Google OAuth failed: email is not verified by auth provider"),
            status_code=307,
        )
    if not auth_user_id:
        return RedirectResponse(
            url=build_frontend_login_redirect(error="Google OAuth failed: missing user id"),
            status_code=307,
        )

    try:
        ensure_user_profile(
            auth_user_id=str(auth_user_id),
            email=str(email),
            pseudo_seed=pseudo_seed,
            avatar_url=google_avatar_url,
        )
    except HTTPException as exc:
        return RedirectResponse(
            url=build_frontend_login_redirect(error=f"Google profile provisioning failed: {exc.detail}"),
            status_code=307,
        )

    if not app_access_token:
        return RedirectResponse(
            url=build_frontend_login_redirect(error="Google OAuth failed: missing application access token"),
            status_code=307,
        )

    response = RedirectResponse(
        url=build_frontend_login_redirect(access_token=app_access_token, refresh_token=app_refresh_token),
        status_code=307,
    )
    if app_refresh_token:
        set_refresh_cookie(response, app_refresh_token)
    return response
