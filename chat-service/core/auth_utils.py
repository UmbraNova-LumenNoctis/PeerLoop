"""Authentication helpers for chat HTTP and WebSocket routes."""

from fastapi import HTTPException, WebSocket

from core.context import INTERNAL_SERVICE_TOKEN, require_supabase


def resolve_user_id(x_user_id: str | None, x_access_token: str | None) -> str | None:
    """Resolve user id from forwarded header or access token.
    
    Args:
        x_user_id (str | None): Identifier for x user.
        x_access_token (str | None): Parameter x_access_token.
    
    Returns:
        str | None: User id from forwarded header or access token.
    """
    if x_user_id:
        return x_user_id

    if x_access_token:
        try:
            user_resp = require_supabase().auth.get_user(x_access_token)
            user_obj = getattr(user_resp, "user", None)
            if user_obj and getattr(user_obj, "id", None):
                return str(user_obj.id)
        except HTTPException:
            raise
        except Exception:
            return None

    return None


def extract_bearer_token(authorization_header: str | None) -> str | None:
    """Extract bearer token from Authorization header.
    
    Args:
        authorization_header (str | None): Parameter authorization_header.
    
    Returns:
        str | None: Bearer token from Authorization header.
    """
    if not isinstance(authorization_header, str):
        return None
    if not authorization_header.lower().startswith("bearer "):
        return None

    parts = authorization_header.split(None, 1)
    if len(parts) < 2:
        return None
    return parts[1].strip()


def resolve_ws_user_id(websocket: WebSocket) -> str | None:
    """Resolve user id from websocket query/header access token.
    
    Args:
        websocket (WebSocket): WebSocket connection.
    
    Returns:
        str | None: User id from websocket query/header access token.
    """
    token = websocket.query_params.get("token") or websocket.query_params.get("access_token")
    if not token:
        token = websocket.headers.get("x-access-token")
    if not token:
        token = extract_bearer_token(websocket.headers.get("authorization"))
    if not token:
        return None

    return resolve_user_id(None, token)


def is_internal_token_valid(x_internal_service_token: str | None) -> bool:
    """Validate trusted internal service token.
    
    Args:
        x_internal_service_token (str | None): Parameter x_internal_service_token.
    
    Returns:
        bool: True if internal token valid, otherwise False.
    """
    if not INTERNAL_SERVICE_TOKEN:
        return False
    return bool(x_internal_service_token and x_internal_service_token == INTERNAL_SERVICE_TOKEN)
