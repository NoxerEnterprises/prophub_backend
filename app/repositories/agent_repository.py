from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agent_profile import AgentProfile


class AgentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, agent: AgentProfile) -> AgentProfile:
        self.session.add(agent)
        await self.session.flush()
        return agent

    async def get_by_id(self, agent_id: uuid.UUID) -> AgentProfile | None:
        statement = select(AgentProfile).where(AgentProfile.id == agent_id).options(selectinload(AgentProfile.user))
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: uuid.UUID) -> AgentProfile | None:
        statement = select(AgentProfile).where(AgentProfile.user_id == user_id).options(selectinload(AgentProfile.user))
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_agents(self, *, page: int = 1, limit: int = 20, status: str | None = None, q: str | None = None) -> tuple[list[AgentProfile], int]:
        filters = []
        if status:
            filters.append(AgentProfile.status == status)
        if q:
            search = f"%{q.strip()}%"
            filters.append(
                or_(
                    AgentProfile.business_name.ilike(search),
                    AgentProfile.business_email.ilike(search),
                    AgentProfile.business_phone.ilike(search),
                    AgentProfile.state.ilike(search),
                    AgentProfile.city.ilike(search),
                )
            )

        base_statement = select(AgentProfile).where(*filters)
        count_statement = select(func.count()).select_from(base_statement.subquery())
        count_result = await self.session.execute(count_statement)
        total = int(count_result.scalar_one() or 0)

        statement = (
            base_statement.options(selectinload(AgentProfile.user))
            .order_by(AgentProfile.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().unique().all()), total
