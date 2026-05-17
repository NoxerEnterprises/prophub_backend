from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.core.enums import UserRole
from app.schemas.common import ORMModel


class UserPublic(ORMModel):
    id: UUID
    email: EmailStr
    phone: str | None = None
    full_name: str
    role: UserRole
    is_active: bool
    is_email_verified: bool
    created_at: datetime
    updated_at: datetime


class CurrentUserResponse(UserPublic):
    agent_status: str | None = None
    is_super_admin: bool = False


class RegisterRequest(ORMModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    phone: str | None = Field(default=None, max_length=32)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).lower().strip()

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class LoginRequest(ORMModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).lower().strip()
