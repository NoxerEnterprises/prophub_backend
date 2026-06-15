from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enums import ChatParticipantRole, ChatType, MessageType
from app.schemas.user import UserPublic


class ChatCreateRequest(BaseModel):
    agent_id: UUID
    property_id: UUID | None = None
    initial_message: str | None = Field(default=None, min_length=1, max_length=5000)


class MessageCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    message_type: MessageType = MessageType.TEXT

    @model_validator(mode="after")
    def validate_text_message(self) -> "MessageCreateRequest":
        if self.message_type != MessageType.TEXT:
            raise ValueError("Use the media upload endpoint for IMAGE or VIDEO messages")
        return self


class ChatParticipantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chat_id: UUID
    user_id: UUID
    role: ChatParticipantRole | str
    joined_at: datetime
    left_at: datetime | None = None
    last_read_at: datetime | None = None
    user: UserPublic | None = None


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chat_id: UUID
    sender_id: UUID
    content: str | None = None
    message_type: MessageType | str
    media_url: str | None = None
    media_path: str | None = None
    media_content_type: str | None = None
    media_size_bytes: int | None = None
    read_at: datetime | None = None
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    sender: UserPublic | None = None


class PropertyChatSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    state: str
    community: str | None = None


class ChatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chat_type: ChatType | str
    property_id: UUID | None = None
    created_by_id: UUID
    title: str | None = None
    last_message_id: UUID | None = None
    last_message_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    participants: list[ChatParticipantResponse] = []
    property: PropertyChatSummary | None = None


class ChatListItem(BaseModel):
    id: UUID
    chat_type: ChatType | str
    property_id: UUID | None = None
    title: str | None = None
    last_message_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    participants: list[ChatParticipantResponse] = []
    property: PropertyChatSummary | None = None
    last_message: MessageResponse | None = None
    unread_count: int = 0


class ChatReadResponse(BaseModel):
    chat_id: UUID
    unread_count: int = 0
    last_read_at: datetime
