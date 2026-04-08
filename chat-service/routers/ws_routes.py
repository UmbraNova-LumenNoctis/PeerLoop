"""WebSocket routes for realtime chat and presence."""

import json
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.auth_utils import resolve_ws_user_id
from services.connection_manager import connection_manager
from utils.content_utils import normalize_content
from stores.conversation_store import ensure_conversation_exists
from services.conversation_visibility import ensure_user_visible_participant
from services.message_flow import create_and_broadcast_message
from stores.message_store import mark_conversation_read

ws_router = APIRouter()


async def disconnect_and_broadcast_leave(
    conversation_id_str: str,
    resolved_user_id: str,
    websocket: WebSocket,
) -> None:
    """Detach websocket and notify conversation presence change when needed.
    
    Args:
        conversation_id_str (str): Parameter conversation_id_str.
        resolved_user_id (str): Identifier for resolved user.
        websocket (WebSocket): WebSocket connection.
    
    Returns:
        None: None.
    """
    user_left_conversation = connection_manager.disconnect(conversation_id_str, resolved_user_id, websocket)
    if user_left_conversation:
        await connection_manager.broadcast(
            conversation_id_str,
            {
                "type": "presence",
                "event": "leave",
                "conversation_id": conversation_id_str,
                "user_id": resolved_user_id,
            },
        )


@ws_router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: UUID):
    """Realtime conversation websocket endpoint.
    
    Args:
        websocket (WebSocket): WebSocket connection.
        conversation_id (UUID): Conversation identifier.
    
    Returns:
        Any: Result of the operation.
    """
    conversation_id_str = str(conversation_id)
    resolved_user_id = resolve_ws_user_id(websocket)
    if not resolved_user_id:
        await websocket.close(code=4401)
        return

    try:
        ensure_conversation_exists(conversation_id_str)
        ensure_user_visible_participant(conversation_id_str, resolved_user_id)
    except Exception as exc:
        status_code = getattr(exc, "status_code", 500)
        if status_code == 404:
            await websocket.close(code=4404)
            return
        if status_code == 403:
            await websocket.close(code=4403)
            return
        await websocket.close(code=1011)
        return

    await connection_manager.connect(conversation_id_str, resolved_user_id, websocket)
    await connection_manager.broadcast(
        conversation_id_str,
        {
            "type": "presence",
            "event": "join",
            "conversation_id": conversation_id_str,
            "user_id": resolved_user_id,
        },
    )
    mark_conversation_read(conversation_id_str, resolved_user_id)
    await websocket.send_json(
        {
            "type": "connected",
            "conversation_id": conversation_id_str,
            "user_id": resolved_user_id,
        }
    )

    try:
        while True:
            raw_message = await websocket.receive_text()
            try:
                payload = json.loads(raw_message)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "detail": "Invalid JSON payload"})
                continue

            message_type = payload.get("type", "message")
            if message_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            if message_type != "message":
                await websocket.send_json({"type": "error", "detail": "Unsupported message type"})
                continue

            content = normalize_content(payload.get("content"))
            if not content:
                await websocket.send_json({"type": "error", "detail": "Message content cannot be empty"})
                continue

            try:
                ensure_user_visible_participant(conversation_id_str, resolved_user_id)
            except Exception as exc:
                detail = str(getattr(exc, "detail", "Forbidden"))
                status_code = getattr(exc, "status_code", 500)
                await websocket.send_json({"type": "error", "detail": detail})
                await disconnect_and_broadcast_leave(conversation_id_str, resolved_user_id, websocket)
                try:
                    await websocket.close(code=4403 if status_code in (403, 404) else 1011)
                except Exception:
                    pass
                return

            try:
                await create_and_broadcast_message(conversation_id_str, resolved_user_id, content)
            except Exception as exc:
                detail = str(getattr(exc, "detail", "Message processing failed"))
                await websocket.send_json({"type": "error", "detail": detail})
    except WebSocketDisconnect:
        await disconnect_and_broadcast_leave(conversation_id_str, resolved_user_id, websocket)
    except Exception:
        await disconnect_and_broadcast_leave(conversation_id_str, resolved_user_id, websocket)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass


@ws_router.websocket("/ws/presence")
async def websocket_presence(websocket: WebSocket):
    """Realtime presence websocket endpoint.
    
    Args:
        websocket (WebSocket): WebSocket connection.
    
    Returns:
        Any: Result of the operation.
    """
    resolved_user_id = resolve_ws_user_id(websocket)
    if not resolved_user_id:
        await websocket.close(code=4401)
        return

    await connection_manager.connect_presence(resolved_user_id, websocket)
    await websocket.send_json(
        {
            "type": "connected",
            "scope": "presence",
            "user_id": resolved_user_id,
        }
    )

    try:
        while True:
            raw_message = await websocket.receive_text()
            try:
                payload = json.loads(raw_message)
            except json.JSONDecodeError:
                continue

            if payload.get("type") == "ping":
                await websocket.send_json({"type": "pong", "scope": "presence"})
    except WebSocketDisconnect:
        connection_manager.disconnect_presence(resolved_user_id, websocket)
    except Exception:
        connection_manager.disconnect_presence(resolved_user_id, websocket)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
