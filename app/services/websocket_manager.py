from __future__ import annotations

import uuid
from collections import defaultdict

from fastapi import WebSocket


class WebSocketConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[uuid.UUID, dict[WebSocket, uuid.UUID]] = defaultdict(dict)

    async def connect(self, *, chat_id: uuid.UUID, user_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[chat_id][websocket] = user_id

    def disconnect(self, *, chat_id: uuid.UUID, websocket: WebSocket) -> None:
        connections = self._connections.get(chat_id)
        if not connections:
            return
        connections.pop(websocket, None)
        if not connections:
            self._connections.pop(chat_id, None)

    async def disconnect_user(self, *, user_id: uuid.UUID, code: int = 4403) -> int:
        disconnected = 0
        for chat_id, connections in list(self._connections.items()):
            for websocket, connection_user_id in list(connections.items()):
                if connection_user_id != user_id:
                    continue
                try:
                    await websocket.close(code=code)
                except Exception:
                    pass
                self.disconnect(chat_id=chat_id, websocket=websocket)
                disconnected += 1
        return disconnected

    async def broadcast(self, *, chat_id: uuid.UUID, payload: dict) -> None:
        stale_connections: list[WebSocket] = []
        for connection in list(self._connections.get(chat_id, {})):
            try:
                await connection.send_json(payload)
            except Exception:
                stale_connections.append(connection)
        for connection in stale_connections:
            self.disconnect(chat_id=chat_id, websocket=connection)


websocket_manager = WebSocketConnectionManager()
