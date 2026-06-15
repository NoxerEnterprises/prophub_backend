from __future__ import annotations

import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.enums import TokenType
from app.core.security import decode_jwt_token
from app.db.session import AsyncSessionLocal
from app.repositories.user_repository import UserRepository
from app.schemas.chat import MessageResponse
from app.services.chat_service import ChatService
from app.services.websocket_manager import websocket_manager

router = APIRouter(prefix="/ws", tags=["WebSocket Chat"])


@router.websocket("/chats/{chat_id}")
async def chat_websocket(websocket: WebSocket, chat_id: uuid.UUID) -> None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    async with AsyncSessionLocal() as session:
        try:
            payload = decode_jwt_token(token, expected_type=TokenType.ACCESS)
            user_id = uuid.UUID(str(payload.get("sub")))
            user = await UserRepository(session).get_by_id(user_id)
            if not user or not user.is_active:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
            await ChatService(session).get_chat_for_user(chat_id=chat_id, current_user=user)
        except Exception:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await websocket_manager.connect(chat_id=chat_id, websocket=websocket)
        try:
            while True:
                event = await websocket.receive_json()
                event_type = event.get("type")
                data = event.get("data") or {}
                if event_type == "message.send":
                    content = str(data.get("content") or "").strip()
                    message = await ChatService(session).send_text_message(chat_id=chat_id, current_user=user, content=content)
                    response = {"type": "message.created", "data": MessageResponse.model_validate(message).model_dump(mode="json")}
                    await websocket_manager.broadcast(chat_id=chat_id, payload=response)
                elif event_type == "chat.read":
                    read_at = await ChatService(session).mark_chat_read(chat_id=chat_id, current_user=user)
                    await websocket.send_json({"type": "chat.read", "data": {"chat_id": str(chat_id), "last_read_at": read_at.isoformat(), "unread_count": 0}})
                else:
                    await websocket.send_json({"type": "error", "data": {"message": "Unsupported event type"}})
        except WebSocketDisconnect:
            websocket_manager.disconnect(chat_id=chat_id, websocket=websocket)
        except Exception as exc:
            await websocket.send_json({"type": "error", "data": {"message": str(exc)}})
            websocket_manager.disconnect(chat_id=chat_id, websocket=websocket)
