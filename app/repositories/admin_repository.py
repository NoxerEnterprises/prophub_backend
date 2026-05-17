from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_activity_log import AdminActivityLog
from app.models.admin_profile import AdminProfile


class AdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_profile(self, profile: AdminProfile) -> AdminProfile:
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def add_activity_log(self, log: AdminActivityLog) -> AdminActivityLog:
        self.session.add(log)
        await self.session.flush()
        return log

    async def list_activity_logs(self, page: int = 1, limit: int = 20) -> tuple[list[AdminActivityLog], int]:
        from sqlalchemy import func

        count_result = await self.session.execute(select(func.count()).select_from(AdminActivityLog))
        total = int(count_result.scalar_one() or 0)
        statement = select(AdminActivityLog).order_by(AdminActivityLog.created_at.desc()).offset((page - 1) * limit).limit(limit)
        result = await self.session.execute(statement)
        return list(result.scalars().all()), total

    async def get_profile_by_user_id(self, user_id: uuid.UUID) -> AdminProfile | None:
        statement = select(AdminProfile).where(AdminProfile.user_id == user_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
