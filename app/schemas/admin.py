from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import ORMModel
from app.schemas.user import UserPublic


class AdminActivityLogResponse(ORMModel):
    id: UUID
    admin_id: UUID
    action: str
    target_type: str
    target_id: UUID | None = None
    description: str | None = None
    metadata_json: dict
    created_at: datetime


class AdminProfileResponse(ORMModel):
    id: UUID
    user_id: UUID
    title: str | None = None
    is_super_admin: bool
    permissions: dict
    created_at: datetime
    updated_at: datetime
    user: UserPublic


class AdminCreateRequest(ORMModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    phone: str | None = Field(default=None, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    is_super_admin: bool = False
    title: str | None = Field(default=None, max_length=120)
    permissions: dict = Field(default_factory=dict)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).lower().strip()


class AdminUpdateRequest(ORMModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: str | None = Field(default=None, max_length=32)
    title: str | None = Field(default=None, max_length=120)
    permissions: dict | None = None


# Backwards compatible alias for older import sites.
CreateAdminRequest = AdminCreateRequest
