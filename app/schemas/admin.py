from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import ORMModel


class AdminActivityLogResponse(ORMModel):
    id: UUID
    admin_id: UUID
    action: str
    target_type: str
    target_id: UUID | None = None
    description: str | None = None
    metadata_json: dict
    created_at: datetime


class CreateAdminRequest(ORMModel):
    email: str
    full_name: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=8, max_length=128)
    is_super_admin: bool = False
    title: str | None = Field(default=None, max_length=120)
