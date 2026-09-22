from __future__ import annotations

from collections.abc import Iterable
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


async def refresh_for_response(
    session: AsyncSession,
    instance: ModelT,
    *,
    relationships: Iterable[str] = (),
) -> ModelT:
    """Refresh scalar DB-generated values and explicitly requested relationships.

    SQLAlchemy may expire server-generated columns (for example ``updated_at``)
    after an INSERT/UPDATE even when ``expire_on_commit=False``. Pydantic's
    synchronous attribute access must never trigger async lazy IO, so mutation
    services should call this helper before returning ORM objects to routes.
    """
    await session.refresh(instance)
    relationship_names = list(relationships)
    if relationship_names:
        await session.refresh(instance, attribute_names=relationship_names)
    return instance
