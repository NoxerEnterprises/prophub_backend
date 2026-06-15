from __future__ import annotations

import uuid
from collections import defaultdict

from fastapi import WebSocket


class WebSocketConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[uuid.UUID, set[WebSocket]] = defaultdict(set)

    async def connect(self, *, chat_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[chat_id].add(websocket)

    def disconnect(self, *, chat_id: uuid.UUID, websocket: WebSocket) -> None:
        connections = self._connections.get(chat_id)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            self._connections.pop(chat_id, None)

    async def broadcast(self, *, chat_id: uuid.UUID, payload: dict) -> None:
        stale_connections: list[WebSocket] = []
        for connection in list(self._connections.get(chat_id, set())):
            try:
                await connection.send_json(payload)
            except RuntimeError:
                stale_connections.append(connection)
        for connection in stale_connections:
            self.disconnect(chat_id=chat_id, websocket=connection)


websocket_manager = WebSocketConnectionManager()
