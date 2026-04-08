"""Chat WebSocket URL helper routes."""

from fastapi import APIRouter, Depends, Request

from routers.security import require_bearer_token

chat_ws_router = APIRouter()


def _build_ws_base_url(request: Request, ws_path: str) -> str:
    """Build an absolute ws/wss URL from forwarded headers and request metadata.
    
    Args:
        request (Request): Incoming FastAPI request context.
        ws_path (str): Parameter ws_path.
    
    Returns:
        str: Absolute ws/wss URL from forwarded headers and request metadata.
    """
    forwarded_proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "").lower()
    ws_scheme = "wss" if forwarded_proto == "https" else "ws"
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    forwarded_port = request.headers.get("x-forwarded-port")
    if host and ":" not in host and forwarded_port and forwarded_port not in {"80", "443"}:
        host = f"{host}:{forwarded_port}"
    return f"{ws_scheme}://{host}{ws_path}"


@chat_ws_router.get(
    "/ws-url/{conversation_id}",
    summary="Get WebSocket URL",
    description="Return ready-to-use ws/wss URL for real-time chat with token query parameter.",
)
async def get_websocket_url(
    conversation_id: str,
    request: Request,
    token: str = Depends(require_bearer_token),
):
    """Return an authenticated WebSocket URL for one conversation.
    
    Args:
        conversation_id (str): Conversation identifier.
        request (Request): Incoming FastAPI request context.
        token (str): Access token.
    
    Returns:
        Any: Authenticated WebSocket URL for one conversation.
    """
    base_ws_url = _build_ws_base_url(request, f"/ws/chat/{conversation_id}")
    return {
        "conversation_id": conversation_id,
        "ws_url": f"{base_ws_url}?token={token}",
        "ws_url_template": f"{base_ws_url}?token=<access_token>",
        "auth_alternative_headers": {
            "Authorization": "Bearer <access_token>",
            "x-access-token": "<access_token>",
        },
    }


@chat_ws_router.get(
    "/presence-ws-url",
    summary="Get Presence WebSocket URL",
    description="Return ready-to-use ws/wss URL for global online presence with token query parameter.",
)
async def get_presence_websocket_url(
    request: Request,
    token: str = Depends(require_bearer_token),
):
    """Return an authenticated WebSocket URL for global presence.
    
    Args:
        request (Request): Incoming FastAPI request context.
        token (str): Access token.
    
    Returns:
        Any: Authenticated WebSocket URL for global presence.
    """
    base_ws_url = _build_ws_base_url(request, "/ws/presence")
    return {
        "ws_url": f"{base_ws_url}?token={token}",
        "ws_url_template": f"{base_ws_url}?token=<access_token>",
        "auth_alternative_headers": {
            "Authorization": "Bearer <access_token>",
            "x-access-token": "<access_token>",
        },
    }
