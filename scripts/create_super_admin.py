import asyncio
import sys

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.admin_profile import AdminProfile
from app.models.user import User
from app.repositories.admin_repository import AdminRepository
from app.repositories.user_repository import UserRepository


async def create_super_admin(email: str, full_name: str, password: str) -> None:
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        users = UserRepository(session)
        admins = AdminRepository(session)
        normalized_email = email.lower().strip()
        existing = await users.get_by_email(normalized_email)
        if existing:
            if existing.role != UserRole.SUPER_ADMIN.value:
                existing.role = UserRole.SUPER_ADMIN.value
            profile = await admins.get_profile_by_user_id(existing.id)
            if not profile:
                await admins.add_profile(AdminProfile(user_id=existing.id, title="Super Admin", is_super_admin=True, permissions={"*": True}))
            else:
                profile.is_super_admin = True
                profile.title = profile.title or "Super Admin"
            await session.commit()
            print(f"Updated existing user as super admin: {normalized_email}")
            return

        user = User(
            email=normalized_email,
            full_name=full_name.strip(),
            hashed_password=hash_password(password),
            role=UserRole.SUPER_ADMIN.value,
            is_active=True,
            is_email_verified=True,
        )
        await users.add(user)
        await admins.add_profile(AdminProfile(user_id=user.id, title="Super Admin", is_super_admin=True, permissions={"*": True}))
        await session.commit()
        print(f"Created super admin: {normalized_email}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print('Usage: python scripts/create_super_admin.py admin@example.com "Admin Name" "StrongPassword123!"')
        raise SystemExit(1)
    asyncio.run(create_super_admin(sys.argv[1], sys.argv[2], sys.argv[3]))
