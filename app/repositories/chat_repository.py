from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import ChatType
from app.models.chat import Chat
from app.models.chat_participant import ChatParticipant
from app.models.message import Message


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_chat(self, chat: Chat) -> Chat:
        self.session.add(chat)
        await self.session.flush()
        return chat

    async def add_participant(self, participant: ChatParticipant) -> ChatParticipant:
        self.session.add(participant)
        await self.session.flush()
        return participant

    async def add_message(self, message: Message) -> Message:
        self.session.add(message)
        await self.session.flush()
        return message

    async def get_chat_by_id(self, chat_id: uuid.UUID) -> Chat | None:
        statement = (
            select(Chat)
            .where(Chat.id == chat_id)
            .options(
                selectinload(Chat.participants).selectinload(ChatParticipant.user),
                selectinload(Chat.property),
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_participant(self, *, chat_id: uuid.UUID, user_id: uuid.UUID) -> ChatParticipant | None:
        statement = (
            select(ChatParticipant)
            .where(ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == user_id, ChatParticipant.left_at.is_(None))
            .options(selectinload(ChatParticipant.user))
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_private_chat_between(
        self,
        *,
        user_a_id: uuid.UUID,
        user_b_id: uuid.UUID,
        property_id: uuid.UUID | None,
    ) -> Chat | None:
        p1 = select(ChatParticipant.chat_id).where(ChatParticipant.user_id == user_a_id, ChatParticipant.left_at.is_(None)).subquery()
        p2 = select(ChatParticipant.chat_id).where(ChatParticipant.user_id == user_b_id, ChatParticipant.left_at.is_(None)).subquery()
        statement = (
            select(Chat)
            .where(
                Chat.chat_type == ChatType.PRIVATE.value,
                Chat.id.in_(select(p1.c.chat_id)),
                Chat.id.in_(select(p2.c.chat_id)),
                (Chat.property_id == property_id if property_id else Chat.property_id.is_(None)),
            )
            .options(selectinload(Chat.participants).selectinload(ChatParticipant.user), selectinload(Chat.property))
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_user_chats(self, *, user_id: uuid.UUID, page: int = 1, limit: int = 20) -> tuple[list[Chat], int]:
        base = (
            select(Chat)
            .join(ChatParticipant, ChatParticipant.chat_id == Chat.id)
            .where(ChatParticipant.user_id == user_id, ChatParticipant.left_at.is_(None))
        )
        count = await self.session.execute(select(func.count()).select_from(base.subquery()))
        total = int(count.scalar_one() or 0)
        statement = (
            base.options(selectinload(Chat.participants).selectinload(ChatParticipant.user), selectinload(Chat.property))
            .order_by(desc(Chat.last_message_at).nullslast(), desc(Chat.created_at))
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().unique().all()), total

    async def list_messages(self, *, chat_id: uuid.UUID, page: int = 1, limit: int = 50) -> tuple[list[Message], int]:
        base = select(Message).where(Message.chat_id == chat_id, Message.deleted_at.is_(None))
        count = await self.session.execute(select(func.count()).select_from(base.subquery()))
        total = int(count.scalar_one() or 0)
        statement = (
            base.options(selectinload(Message.sender))
            .order_by(Message.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        messages = list(result.scalars().unique().all())
        messages.reverse()
        return messages, total

    async def get_last_message(self, chat_id: uuid.UUID) -> Message | None:
        statement = (
            select(Message)
            .where(Message.chat_id == chat_id, Message.deleted_at.is_(None))
            .options(selectinload(Message.sender))
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def count_unread(self, *, chat_id: uuid.UUID, user_id: uuid.UUID, last_read_at: datetime | None) -> int:
        filters = [Message.chat_id == chat_id, Message.sender_id != user_id, Message.deleted_at.is_(None)]
        if last_read_at is not None:
            filters.append(Message.created_at > last_read_at)
        statement = select(func.count()).select_from(Message).where(and_(*filters))
        result = await self.session.execute(statement)
        return int(result.scalar_one() or 0)

    async def mark_read(self, *, participant: ChatParticipant, read_at: datetime) -> ChatParticipant:
        participant.last_read_at = read_at
        await self.session.flush()
        return participant
