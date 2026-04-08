"""WebSocket connection manager for conversations and global presence."""

import asyncio
from collections import defaultdict
from threading import Lock

from fastapi import WebSocket


class ConversationConnectionManager:
    """Track sockets by conversation and user, and broadcast events safely."""

    def __init__(self):
        """Initialize empty connection registries and the synchronization lock.
        
        Returns:
            None: None.
        """
        self._conversation_connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._conversation_user_connections: dict[str, dict[str, set[WebSocket]]] = defaultdict(
            lambda: defaultdict(set)
        )
        self._user_connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = Lock()

    async def connect(self, conversation_id: str, user_id: str, websocket: WebSocket) -> None:
        """Accept and register a websocket for a conversation and user.
        
        Args:
            conversation_id (str): Conversation identifier.
            user_id (str): User identifier.
            websocket (WebSocket): WebSocket connection.
        
        Returns:
            None: None.
        """
        await websocket.accept()
        with self._lock:
            self._conversation_connections[conversation_id].add(websocket)
            self._conversation_user_connections[conversation_id][user_id].add(websocket)
            self._user_connections[user_id].add(websocket)

    async def connect_presence(self, user_id: str, websocket: WebSocket) -> None:
        """Accept and register a websocket for global presence only.
        
        Args:
            user_id (str): User identifier.
            websocket (WebSocket): WebSocket connection.
        
        Returns:
            None: None.
        """
        await websocket.accept()
        with self._lock:
            self._user_connections[user_id].add(websocket)

    def disconnect(self, conversation_id: str, user_id: str, websocket: WebSocket) -> bool:
        """Remove a websocket from conversation and user registries.
        
        Args:
            conversation_id (str): Conversation identifier.
            user_id (str): User identifier.
            websocket (WebSocket): WebSocket connection.
        
        Returns:
            bool: Result of the operation.
        """
        user_left_conversation = False
        with self._lock:
            conversation_connections = self._conversation_connections.get(conversation_id)
            if conversation_connections:
                conversation_connections.discard(websocket)
                if not conversation_connections:
                    self._conversation_connections.pop(conversation_id, None)

            conversation_user_connections = self._conversation_user_connections.get(conversation_id)
            if conversation_user_connections:
                user_conversation_connections = conversation_user_connections.get(user_id)
                if user_conversation_connections is not None:
                    user_conversation_connections.discard(websocket)
                    if not user_conversation_connections:
                        conversation_user_connections.pop(user_id, None)
                        user_left_conversation = True
                if not conversation_user_connections:
                    self._conversation_user_connections.pop(conversation_id, None)

            user_connections = self._user_connections.get(user_id)
            if user_connections:
                user_connections.discard(websocket)
                if not user_connections:
                    self._user_connections.pop(user_id, None)

        return user_left_conversation

    def disconnect_presence(self, user_id: str, websocket: WebSocket) -> None:
        """Remove a presence-only websocket for a user.
        
        Args:
            user_id (str): User identifier.
            websocket (WebSocket): WebSocket connection.
        
        Returns:
            None: None.
        """
        with self._lock:
            user_connections = self._user_connections.get(user_id)
            if user_connections:
                user_connections.discard(websocket)
                if not user_connections:
                    self._user_connections.pop(user_id, None)

    async def _safe_send_json(self, websocket: WebSocket, payload: dict) -> bool:
        """Send a JSON payload and report whether it succeeded.
        
        Args:
            websocket (WebSocket): WebSocket connection.
            payload (dict): Parsed request payload.
        
        Returns:
            bool: Result of the operation.
        """
        try:
            await websocket.send_json(payload)
            return True
        except Exception:
            return False

    async def broadcast(self, conversation_id: str, payload: dict) -> None:
        """Broadcast a JSON payload to all sockets in a conversation.
        
        Args:
            conversation_id (str): Conversation identifier.
            payload (dict): Parsed request payload.
        
        Returns:
            None: None.
        """
        with self._lock:
            targets = list(self._conversation_connections.get(conversation_id, set()))

        if not targets:
            return

        sent_results = await asyncio.gather(
            *(self._safe_send_json(websocket, payload) for websocket in targets)
        )
        for websocket, sent in zip(targets, sent_results):
            if not sent:
                self._remove_socket_from_all(conversation_id, websocket)

    def get_online_user_ids(self, user_ids: list[str] | None = None) -> set[str]:
        """Return the set of user ids that currently have active sockets.
        
        Args:
            user_ids (list[str] | None): Identifiers for user.
        
        Returns:
            set[str]: Set of user ids that currently have active sockets.
        """
        with self._lock:
            online_ids = {user_id for user_id, sockets in self._user_connections.items() if sockets}
        if user_ids is None:
            return online_ids
        return {user_id for user_id in user_ids if user_id in online_ids}

    def _remove_socket_from_all(self, conversation_id: str, websocket: WebSocket) -> None:
        """Remove a websocket from all registries and clean up empty buckets.
        
        Args:
            conversation_id (str): Conversation identifier.
            websocket (WebSocket): WebSocket connection.
        
        Returns:
            None: None.
        """
        with self._lock:
            conversation_connections = self._conversation_connections.get(conversation_id)
            if conversation_connections:
                conversation_connections.discard(websocket)
                if not conversation_connections:
                    self._conversation_connections.pop(conversation_id, None)

            conversation_user_connections = self._conversation_user_connections.get(conversation_id)
            if conversation_user_connections:
                empty_user_ids = []
                for user_id, sockets in conversation_user_connections.items():
                    sockets.discard(websocket)
                    if not sockets:
                        empty_user_ids.append(user_id)
                for user_id in empty_user_ids:
                    conversation_user_connections.pop(user_id, None)
                if not conversation_user_connections:
                    self._conversation_user_connections.pop(conversation_id, None)

            empty_user_ids = []
            for user_id, sockets in self._user_connections.items():
                if websocket in sockets:
                    sockets.discard(websocket)
                if not sockets:
                    empty_user_ids.append(user_id)
            for user_id in empty_user_ids:
                self._user_connections.pop(user_id, None)

    def detach_user_from_conversation(self, conversation_id: str, user_id: str) -> list[WebSocket]:
        """Detach all sockets for a user from a conversation.
        
        Args:
            conversation_id (str): Conversation identifier.
            user_id (str): User identifier.
        
        Returns:
            list[WebSocket]: Result of the operation.
        """
        with self._lock:
            conversation_user_connections = self._conversation_user_connections.get(conversation_id)
            if not conversation_user_connections:
                return []

            sockets = list(conversation_user_connections.pop(user_id, set()))
            if not conversation_user_connections:
                self._conversation_user_connections.pop(conversation_id, None)

            if not sockets:
                return []

            conversation_connections = self._conversation_connections.get(conversation_id)
            user_connections = self._user_connections.get(user_id)
            for websocket in sockets:
                if conversation_connections:
                    conversation_connections.discard(websocket)
                if user_connections:
                    user_connections.discard(websocket)

            if conversation_connections is not None and not conversation_connections:
                self._conversation_connections.pop(conversation_id, None)
            if user_connections is not None and not user_connections:
                self._user_connections.pop(user_id, None)

        return sockets


connection_manager = ConversationConnectionManager()
