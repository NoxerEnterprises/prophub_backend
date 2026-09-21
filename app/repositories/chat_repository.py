from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import ChatType
from app.models.chat import Chat
from app.models.chat_participant import ChatParticipant
from app.models.message import Message


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _chat_options():
        return (
            selectinload(Chat.participants).selectinload(ChatParticipant.user),
            selectinload(Chat.property),
            selectinload(Chat.target_user),
            selectinload(Chat.underlying_agent),
        )

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
        result = await self.session.execute(
            select(Chat).where(Chat.id == chat_id).options(*self._chat_options())
        )
        return result.scalar_one_or_none()

    async def get_participant(self, *, chat_id: uuid.UUID, user_id: uuid.UUID) -> ChatParticipant | None:
        result = await self.session.execute(
            select(ChatParticipant)
            .where(
                ChatParticipant.chat_id == chat_id,
                ChatParticipant.user_id == user_id,
                ChatParticipant.left_at.is_(None),
            )
            .options(selectinload(ChatParticipant.user))
        )
        return result.scalar_one_or_none()

    async def get_participant_any(self, *, chat_id: uuid.UUID, user_id: uuid.UUID) -> ChatParticipant | None:
        result = await self.session.execute(
            select(ChatParticipant)
            .where(ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == user_id)
            .options(selectinload(ChatParticipant.user))
        )
        return result.scalar_one_or_none()

    async def get_private_chat_between(
        self,
        *,
        user_a_id: uuid.UUID,
        user_b_id: uuid.UUID,
        property_id: uuid.UUID | None,
    ) -> Chat | None:
        p1 = select(ChatParticipant.chat_id).where(
            ChatParticipant.user_id == user_a_id,
            ChatParticipant.left_at.is_(None),
        ).subquery()
        p2 = select(ChatParticipant.chat_id).where(
            ChatParticipant.user_id == user_b_id,
            ChatParticipant.left_at.is_(None),
        ).subquery()
        statement = (
            select(Chat)
            .where(
                Chat.chat_type == ChatType.PRIVATE.value,
                Chat.id.in_(select(p1.c.chat_id)),
                Chat.id.in_(select(p2.c.chat_id)),
                Chat.property_id == property_id if property_id else Chat.property_id.is_(None),
            )
            .options(*self._chat_options())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_user_chats(self, *, user_id: uuid.UUID, page: int = 1, limit: int = 20) -> tuple[list[Chat], int]:
        base = (
            select(Chat)
            .join(ChatParticipant, ChatParticipant.chat_id == Chat.id)
            .where(
                ChatParticipant.user_id == user_id,
                ChatParticipant.left_at.is_(None),
                Chat.is_active.is_(True),
            )
        )
        count = await self.session.execute(select(func.count()).select_from(base.subquery()))
        total = int(count.scalar_one() or 0)
        result = await self.session.execute(
            base.options(*self._chat_options())
            .order_by(desc(Chat.last_message_at).nullslast(), desc(Chat.created_at))
            .offset((page - 1) * limit)
            .limit(limit)
        )
        return list(result.scalars().unique().all()), total

    async def list_group_chats(
        self,
        *,
        page: int = 1,
        limit: int = 20,
        country: str | None = None,
        state: str | None = None,
        local_government: str | None = None,
        community: str | None = None,
    ) -> tuple[list[Chat], int]:
        filters = [Chat.chat_type == ChatType.GROUP.value, Chat.is_active.is_(True)]
        if country:
            filters.append(Chat.country.ilike(country.strip()))
        if state:
            filters.append(Chat.state.ilike(state.strip()))
        if local_government:
            filters.append(Chat.local_government.ilike(local_government.strip()))
        if community:
            filters.append(Chat.community.ilike(community.strip()))
        base = select(Chat).where(*filters)
        count = await self.session.execute(select(func.count()).select_from(base.subquery()))
        total = int(count.scalar_one() or 0)
        result = await self.session.execute(
            base.options(*self._chat_options())
            .order_by(Chat.state.asc().nullslast(), Chat.local_government.asc().nullslast(), Chat.title.asc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        return list(result.scalars().unique().all()), total

    async def count_active_participants(self, chat_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(ChatParticipant)
            .where(ChatParticipant.chat_id == chat_id, ChatParticipant.left_at.is_(None))
        )
        return int(result.scalar_one() or 0)

    async def list_messages(self, *, chat_id: uuid.UUID, page: int = 1, limit: int = 50) -> tuple[list[Message], int]:
        base = select(Message).where(Message.chat_id == chat_id, Message.deleted_at.is_(None))
        count = await self.session.execute(select(func.count()).select_from(base.subquery()))
        total = int(count.scalar_one() or 0)
        result = await self.session.execute(
            base.options(selectinload(Message.sender), selectinload(Message.shared_property))
            .order_by(Message.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        messages = list(result.scalars().unique().all())
        messages.reverse()
        return messages, total

    async def get_last_message(self, chat_id: uuid.UUID) -> Message | None:
        result = await self.session.execute(
            select(Message)
            .where(Message.chat_id == chat_id, Message.deleted_at.is_(None))
            .options(selectinload(Message.sender), selectinload(Message.shared_property))
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def count_unread(
        self,
        *,
        chat_id: uuid.UUID,
        user_id: uuid.UUID,
        last_read_at: datetime | None,
    ) -> int:
        filters = [Message.chat_id == chat_id, Message.sender_id != user_id, Message.deleted_at.is_(None)]
        if last_read_at is not None:
            filters.append(Message.created_at > last_read_at)
        result = await self.session.execute(select(func.count()).select_from(Message).where(and_(*filters)))
        return int(result.scalar_one() or 0)

    async def mark_read(self, *, participant: ChatParticipant, read_at: datetime) -> ChatParticipant:
        participant.last_read_at = read_at
        await self.session.flush()
        return participant
