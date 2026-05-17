import asyncio

from app.core.config import settings
from scripts.create_super_admin import create_super_admin


async def main() -> None:
    if not settings.FIRST_SUPER_ADMIN_EMAIL or not settings.FIRST_SUPER_ADMIN_PASSWORD:
        raise SystemExit("FIRST_SUPER_ADMIN_EMAIL and FIRST_SUPER_ADMIN_PASSWORD are required in .env")
    await create_super_admin(
        settings.FIRST_SUPER_ADMIN_EMAIL,
        settings.FIRST_SUPER_ADMIN_FULL_NAME or "Super Admin",
        settings.FIRST_SUPER_ADMIN_PASSWORD,
    )


if __name__ == "__main__":
    asyncio.run(main())
