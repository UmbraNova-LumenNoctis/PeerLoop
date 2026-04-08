"""Chat router composition module."""

from fastapi import APIRouter

from routers.chat_conversations import chat_conversations_router
from routers.chat_state import chat_state_router
from routers.chat_ws import chat_ws_router

chat_router = APIRouter(prefix="/api/chat", tags=["Chat"])
chat_router.include_router(chat_conversations_router)
chat_router.include_router(chat_state_router)
chat_router.include_router(chat_ws_router)
