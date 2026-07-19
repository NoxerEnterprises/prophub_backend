from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import UserRole
from app.models.admin_profile import AdminProfile
from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        statement = select(User).where(User.id == user_id).options(
            selectinload(User.agent_profile),
            selectinload(User.admin_profile),
            selectinload(User.documents),
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email.lower().strip()).options(
            selectinload(User.agent_profile),
            selectinload(User.admin_profile),
            selectinload(User.documents),
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> User | None:
        statement = select(User).where(User.phone == phone)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def add(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        return user

    async def list_admin_users(self, *, page: int = 1, limit: int = 20) -> tuple[list[AdminProfile], int]:
        base = select(AdminProfile).join(AdminProfile.user).where(User.role.in_([UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]))
        count_result = await self.session.execute(select(func.count()).select_from(base.subquery()))
        total = int(count_result.scalar_one() or 0)
        result = await self.session.execute(
            base.options(selectinload(AdminProfile.user)).order_by(AdminProfile.created_at.desc()).offset((page - 1) * limit).limit(limit)
        )
        return list(result.scalars().unique().all()), total

    async def get_admin_profile_by_id(self, admin_id: uuid.UUID) -> AdminProfile | None:
        result = await self.session.execute(select(AdminProfile).where(AdminProfile.id == admin_id).options(selectinload(AdminProfile.user)))
        return result.scalar_one_or_none()

    async def get_first_active_super_admin(self) -> User | None:
        statement = (
            select(User)
            .join(AdminProfile, AdminProfile.user_id == User.id)
            .where(User.is_active.is_(True), User.role == UserRole.SUPER_ADMIN.value, AdminProfile.is_super_admin.is_(True))
            .order_by(AdminProfile.created_at.asc())
            .limit(1)
            .options(selectinload(User.admin_profile))
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
