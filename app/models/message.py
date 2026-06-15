from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import MessageType
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.chat import Chat
    from app.models.user import User


class Message(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "messages"

    chat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), index=True, nullable=False)
    sender_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_type: Mapped[str] = mapped_column(String(30), default=MessageType.TEXT.value, index=True, nullable=False)
    media_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    media_size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True, nullable=True)

    chat: Mapped[Chat] = relationship("Chat", back_populates="messages", lazy="selectin")
    sender: Mapped[User] = relationship("User", lazy="selectin")
