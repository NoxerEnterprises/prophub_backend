from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ChatParticipantRole
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.chat import Chat
    from app.models.user import User


class ChatParticipant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "chat_participants"
    __table_args__ = (UniqueConstraint("chat_id", "user_id", name="uq_chat_participants_chat_id_user_id"),)

    chat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(30), default=ChatParticipantRole.MEMBER.value, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    chat: Mapped[Chat] = relationship("Chat", back_populates="participants", lazy="selectin")
    user: Mapped[User] = relationship("User", lazy="selectin")
