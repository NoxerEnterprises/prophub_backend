from __future__ import annotations

import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.enums import TokenType
from app.core.security import decode_jwt_token
from app.db.session import AsyncSessionLocal
from app.repositories.user_repository import UserRepository
from app.services.chat_service import ChatService
from app.services.websocket_manager import websocket_manager
from app.schemas.chat import MessageResponse

router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("/chats/{chat_id}")
async def chat_websocket(websocket: WebSocket, chat_id: uuid.UUID, token: str):
    user_id: uuid.UUID | None = None
    try:
        payload = decode_jwt_token(token, expected_type=TokenType.ACCESS)
        user_id = uuid.UUID(str(payload.get("sub")))
        async with AsyncSessionLocal() as session:
            user = await UserRepository(session).get_by_id(user_id)
            if not user or not user.is_active or not user.is_email_verified:
                await websocket.close(code=4401)
                return
            await ChatService(session).get_chat_for_user(chat_id=chat_id, current_user=user)
        await websocket_manager.connect(chat_id=chat_id, websocket=websocket)
        await websocket.send_json({"type": "connection.ready", "data": {"chat_id": str(chat_id), "user_id": str(user_id)}})
        try:
            while True:
                payload = await websocket.receive_json()
                event_type = payload.get("type")
                data = payload.get("data") or {}
                if event_type == "ping":
                    await websocket.send_json({"type": "pong", "data": {}})
                elif event_type == "message.send":
                    content = data.get("content")
                    client_message_id = data.get("client_message_id")
                    async with AsyncSessionLocal() as session:
                        user = await UserRepository(session).get_by_id(user_id)
                        message = await ChatService(session).send_text_message(chat_id=chat_id, current_user=user, content=content, client_message_id=client_message_id)
                        response = MessageResponse.model_validate(message).model_dump(mode="json")
                    await websocket_manager.broadcast(chat_id=chat_id, payload={"type": "message.created", "data": response})
                elif event_type == "chat.read":
                    async with AsyncSessionLocal() as session:
                        user = await UserRepository(session).get_by_id(user_id)
                        read_at = await ChatService(session).mark_chat_read(chat_id=chat_id, current_user=user)
                    await websocket_manager.broadcast(chat_id=chat_id, payload={"type": "chat.read", "data": {"chat_id": str(chat_id), "user_id": str(user_id), "last_read_at": read_at.isoformat()}})
                else:
                    await websocket.send_json({"type": "error", "data": {"message": "Unsupported event type"}})
        except WebSocketDisconnect:
            websocket_manager.disconnect(chat_id=chat_id, websocket=websocket)
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "data": {"message": str(exc)}})
            await websocket.close(code=1011)
        except Exception:
            pass
        websocket_manager.disconnect(chat_id=chat_id, websocket=websocket)
