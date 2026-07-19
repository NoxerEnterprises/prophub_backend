from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from app.api.dependencies import CurrentUserDep, SessionDep
from app.schemas.chat import ChatCreateRequest, ChatListItem, ChatReadResponse, ChatResponse, MessageCreateRequest, MessageResponse
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.services.chat_service import ChatService
from app.services.websocket_manager import websocket_manager

router = APIRouter(prefix="/chats", tags=["Chats"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=APIResponse[ChatResponse])
async def start_chat(payload: ChatCreateRequest, current_user: CurrentUserDep, session: SessionDep) -> APIResponse[ChatResponse]:
    chat, message = await ChatService(session).start_or_get_private_chat(current_user=current_user, payload=payload)
    if message:
        await websocket_manager.broadcast(chat_id=chat.id, payload={"type": "message.created", "data": MessageResponse.model_validate(message).model_dump(mode="json")})
    return APIResponse(message="Chat ready", data=ChatResponse.model_validate(chat))


@router.get("", response_model=APIResponse[PaginatedResponse[ChatListItem]])
async def list_my_chats(current_user: CurrentUserDep, session: SessionDep, page: int = Query(default=1, ge=1), limit: int = Query(default=20, ge=1, le=100)) -> APIResponse[PaginatedResponse[ChatListItem]]:
    items, total = await ChatService(session).list_my_chats(current_user=current_user, page=page, limit=limit)
    return APIResponse(message="Chats retrieved", data=PaginatedResponse(items=items, meta=PaginationMeta(page=page, limit=limit, total=total)))


@router.get("/{chat_id}", response_model=APIResponse[ChatResponse])
async def get_chat(chat_id: UUID, current_user: CurrentUserDep, session: SessionDep) -> APIResponse[ChatResponse]:
    chat = await ChatService(session).get_chat_for_user(chat_id=chat_id, current_user=current_user)
    return APIResponse(message="Chat retrieved", data=ChatResponse.model_validate(chat))


@router.get("/{chat_id}/messages", response_model=APIResponse[PaginatedResponse[MessageResponse]])
async def list_messages(chat_id: UUID, current_user: CurrentUserDep, session: SessionDep, page: int = Query(default=1, ge=1), limit: int = Query(default=50, ge=1, le=100)) -> APIResponse[PaginatedResponse[MessageResponse]]:
    messages, total = await ChatService(session).list_messages(chat_id=chat_id, current_user=current_user, page=page, limit=limit)
    return APIResponse(message="Messages retrieved", data=PaginatedResponse(items=[MessageResponse.model_validate(message) for message in messages], meta=PaginationMeta(page=page, limit=limit, total=total)))


@router.post("/{chat_id}/messages", status_code=status.HTTP_201_CREATED, response_model=APIResponse[MessageResponse])
async def send_message(chat_id: UUID, payload: MessageCreateRequest, current_user: CurrentUserDep, session: SessionDep) -> APIResponse[MessageResponse]:
    message = await ChatService(session).send_text_message(chat_id=chat_id, current_user=current_user, content=payload.content, client_message_id=payload.client_message_id)
    response = MessageResponse.model_validate(message)
    await websocket_manager.broadcast(chat_id=chat_id, payload={"type": "message.created", "data": response.model_dump(mode="json")})
    return APIResponse(message="Message sent", data=response)


@router.post("/{chat_id}/messages/media", status_code=status.HTTP_201_CREATED, response_model=APIResponse[MessageResponse])
async def upload_media_message(chat_id: UUID, current_user: CurrentUserDep, session: SessionDep, file: Annotated[UploadFile, File(...)], content: Annotated[str | None, Form(max_length=5000)] = None, client_message_id: Annotated[str | None, Form(max_length=120)] = None) -> APIResponse[MessageResponse]:
    message = await ChatService(session).upload_media_message(chat_id=chat_id, current_user=current_user, file=file, content=content, client_message_id=client_message_id)
    response = MessageResponse.model_validate(message)
    await websocket_manager.broadcast(chat_id=chat_id, payload={"type": "message.created", "data": response.model_dump(mode="json")})
    return APIResponse(message="Media message sent", data=response)


@router.patch("/{chat_id}/read", response_model=APIResponse[ChatReadResponse])
async def mark_chat_read(chat_id: UUID, current_user: CurrentUserDep, session: SessionDep) -> APIResponse[ChatReadResponse]:
    read_at = await ChatService(session).mark_chat_read(chat_id=chat_id, current_user=current_user)
    await websocket_manager.broadcast(chat_id=chat_id, payload={"type": "chat.read", "data": {"chat_id": str(chat_id), "user_id": str(current_user.id), "last_read_at": read_at.isoformat()}})
    return APIResponse(message="Chat marked as read", data=ChatReadResponse(chat_id=chat_id, last_read_at=read_at, unread_count=0))
