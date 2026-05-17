from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import now_utc
from app.models.admin_activity_log import AdminActivityLog
from app.repositories.admin_repository import AdminRepository


class AdminActivityService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.admins = AdminRepository(session)

    async def log(
        self,
        *,
        admin_id: uuid.UUID,
        action: str,
        target_type: str,
        target_id: uuid.UUID | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AdminActivityLog:
        log = AdminActivityLog(
            admin_id=admin_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            description=description,
            metadata_json=metadata or {},
            created_at=now_utc(),
        )
        return await self.admins.add_activity_log(log)
