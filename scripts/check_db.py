import asyncio

from app.db.session import check_database_connection


async def main() -> None:
    await check_database_connection()
    print("Database connection successful.")


if __name__ == "__main__":
    asyncio.run(main())
