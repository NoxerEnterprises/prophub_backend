from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.admin_activity_log import AdminAction, AdminActivityLog


class AdminActivityRepository:
    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        *,
        admin_user_id: UUID | None,
        action: AdminAction,
        target_type: str,
        target_id: UUID | None = None,
        description: str | None = None,
        metadata_json: dict | None = None,
    ) -> AdminActivityLog:
        record = AdminActivityLog(
            admin_user_id=admin_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            description=description,
            metadata_json=metadata_json,
        )
        self.db.add(record)
        self.db.flush()
        return record
