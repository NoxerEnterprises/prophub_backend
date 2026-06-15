from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ChatType
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.chat_participant import ChatParticipant
    from app.models.message import Message
    from app.models.property import Property
    from app.models.user import User


class Chat(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "chats"
    __table_args__ = (
        Index("ix_chats_property_id_created_by_id", "property_id", "created_by_id"),
        Index("ix_chats_last_message_at", "last_message_at"),
    )

    chat_type: Mapped[str] = mapped_column(String(30), default=ChatType.PRIVATE.value, index=True, nullable=False)
    property_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="SET NULL"), index=True, nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    last_message_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True, nullable=True)

    created_by: Mapped[User] = relationship("User", lazy="selectin", foreign_keys=[created_by_id])
    property: Mapped[Property | None] = relationship("Property", lazy="selectin")
    participants: Mapped[list[ChatParticipant]] = relationship(
        "ChatParticipant",
        back_populates="chat",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    messages: Mapped[list[Message]] = relationship(
        "Message",
        back_populates="chat",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="Message.created_at.asc()",
    )
