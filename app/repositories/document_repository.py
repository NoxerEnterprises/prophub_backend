from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user_document import UserDocument


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, document: UserDocument) -> UserDocument:
        self.session.add(document)
        await self.session.flush()
        return document

    async def get_by_id(self, document_id: uuid.UUID) -> UserDocument | None:
        result = await self.session.execute(select(UserDocument).where(UserDocument.id == document_id).options(selectinload(UserDocument.user), selectinload(UserDocument.agent_profile)))
        return result.scalar_one_or_none()

    async def get_agent_document(self, *, agent_profile_id: uuid.UUID, document_type: str) -> UserDocument | None:
        result = await self.session.execute(select(UserDocument).where(UserDocument.agent_profile_id == agent_profile_id, UserDocument.document_type == document_type))
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID) -> list[UserDocument]:
        result = await self.session.execute(select(UserDocument).where(UserDocument.user_id == user_id).order_by(UserDocument.created_at.desc()))
        return list(result.scalars().all())

    async def list_for_agent(self, agent_profile_id: uuid.UUID) -> list[UserDocument]:
        result = await self.session.execute(select(UserDocument).where(UserDocument.agent_profile_id == agent_profile_id).order_by(UserDocument.created_at.desc()))
        return list(result.scalars().all())

    async def list_for_admin(self, *, page: int = 1, limit: int = 20, status: str | None = None, document_type: str | None = None, user_id: uuid.UUID | None = None, agent_profile_id: uuid.UUID | None = None) -> tuple[list[UserDocument], int]:
        filters = []
        if status:
            filters.append(UserDocument.status == status)
        if document_type:
            filters.append(UserDocument.document_type == document_type)
        if user_id:
            filters.append(UserDocument.user_id == user_id)
        if agent_profile_id:
            filters.append(UserDocument.agent_profile_id == agent_profile_id)
        base = select(UserDocument).where(*filters)
        total_result = await self.session.execute(select(func.count()).select_from(base.subquery()))
        total = int(total_result.scalar_one() or 0)
        result = await self.session.execute(base.options(selectinload(UserDocument.user), selectinload(UserDocument.agent_profile)).order_by(UserDocument.created_at.desc()).offset((page - 1) * limit).limit(limit))
        return list(result.scalars().unique().all()), total
