from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AdminAction, UserRole, UserType
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.security import hash_password
from app.models.admin_profile import AdminProfile
from app.models.user import User
from app.repositories.admin_repository import AdminRepository
from app.repositories.user_repository import UserRepository
from app.schemas.admin import AdminCreateRequest, AdminUpdateRequest
from app.services.admin_activity_service import AdminActivityService


class AdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.admins = AdminRepository(session)
        self.activity = AdminActivityService(session)

    async def create_admin(self, *, actor: User, payload: AdminCreateRequest) -> AdminProfile:
        if actor.role != UserRole.SUPER_ADMIN.value:
            raise ForbiddenError("Super admin access required")
        existing = await self.users.get_by_email(str(payload.email))
        if existing:
            raise ConflictError("Email is already registered")
        if payload.phone and await self.users.get_by_phone(payload.phone):
            raise ConflictError("Phone number is already registered")
        role = UserRole.SUPER_ADMIN.value if payload.is_super_admin else UserRole.ADMIN.value
        user = User(
            email=str(payload.email).lower().strip(),
            phone=payload.phone,
            full_name=payload.full_name.strip(),
            hashed_password=hash_password(payload.password),
            role=role,
            user_type=UserType.CUSTOMER.value,
            is_active=True,
            is_email_verified=True,
        )
        await self.users.add(user)
        profile = AdminProfile(user_id=user.id, title=payload.title, is_super_admin=payload.is_super_admin, permissions=payload.permissions)
        await self.admins.add_profile(profile)
        await self.activity.log(
            admin_id=actor.id,
            action=AdminAction.ADMIN_CREATED.value,
            target_type="admin_profile",
            target_id=profile.id,
            description=f"Created admin {user.email}",
            metadata={"email": user.email, "is_super_admin": payload.is_super_admin},
        )
        await self.session.commit()
        await self.session.refresh(profile, attribute_names=["user"])
        return profile

    async def list_admins(self, *, page: int, limit: int):
        return await self.users.list_admin_users(page=page, limit=limit)

    async def get_admin(self, admin_id: UUID) -> AdminProfile:
        profile = await self.users.get_admin_profile_by_id(admin_id)
        if not profile:
            raise NotFoundError("Admin not found")
        return profile

    async def update_admin(self, *, actor: User, admin_id: UUID, payload: AdminUpdateRequest) -> AdminProfile:
        if actor.role != UserRole.SUPER_ADMIN.value:
            raise ForbiddenError("Super admin access required")
        profile = await self.get_admin(admin_id)
        update = payload.model_dump(exclude_unset=True)
        if "full_name" in update and update["full_name"] is not None:
            profile.user.full_name = update["full_name"]
        if "phone" in update:
            profile.user.phone = update["phone"]
        if "title" in update:
            profile.title = update["title"]
        if "permissions" in update and update["permissions"] is not None:
            profile.permissions = update["permissions"]
        await self.activity.log(
            admin_id=actor.id,
            action=AdminAction.ADMIN_UPDATED.value,
            target_type="admin_profile",
            target_id=profile.id,
            description="Admin updated",
            metadata=update,
        )
        await self.session.commit()
        await self.session.refresh(profile, attribute_names=["user"])
        return profile

    async def set_admin_active(self, *, actor: User, admin_id: UUID, is_active: bool) -> AdminProfile:
        if actor.role != UserRole.SUPER_ADMIN.value:
            raise ForbiddenError("Super admin access required")
        profile = await self.get_admin(admin_id)
        if profile.user_id == actor.id and not is_active:
            raise ForbiddenError("Super admin cannot disable self")
        profile.user.is_active = is_active
        await self.activity.log(
            admin_id=actor.id,
            action=AdminAction.ADMIN_ENABLED.value if is_active else AdminAction.ADMIN_DISABLED.value,
            target_type="admin_profile",
            target_id=profile.id,
            description="Admin enabled" if is_active else "Admin disabled",
            metadata={"is_active": is_active},
        )
        await self.session.commit()
        await self.session.refresh(profile, attribute_names=["user"])
        return profile
