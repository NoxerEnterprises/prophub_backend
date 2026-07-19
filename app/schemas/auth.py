from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.core.enums import UserRole
from app.schemas.common import ORMModel
from app.schemas.user import CurrentUserResponse, UserPublic


class TokenPair(ORMModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime


class AuthResponse(ORMModel):
    user: UserPublic
    tokens: TokenPair | None = None
    email_verification_required: bool = False
    is_email_verified: bool = False
    debug_verification_token: str | None = None
    debug_otp_code: str | None = None


class EmailVerificationRequest(ORMModel):
    email: EmailStr
    verification_token: str | None = Field(default=None, min_length=20)
    otp_code: str = Field(min_length=4, max_length=10)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).lower().strip()


class EmailVerificationResponse(ORMModel):
    verified: bool
    user: UserPublic
    tokens: TokenPair | None = None


class ResendEmailVerificationRequest(ORMModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).lower().strip()


class ResendEmailVerificationResponse(ORMModel):
    email_verification_required: bool = True
    email: EmailStr
    debug_verification_token: str | None = None
    debug_otp_code: str | None = None


class RefreshTokenRequest(ORMModel):
    refresh_token: str = Field(min_length=20)


class LogoutRequest(ORMModel):
    refresh_token: str = Field(min_length=20)


class PasswordResetRequest(ORMModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).lower().strip()


class PasswordResetRequestResponse(ORMModel):
    message: str
    debug_reset_token: str | None = None
    debug_otp_code: str | None = None


class PasswordResetVerifyRequest(ORMModel):
    reset_token: str = Field(min_length=20)
    otp_code: str = Field(min_length=4, max_length=10)


class PasswordResetVerifyResponse(ORMModel):
    valid: bool


class PasswordResetConfirmRequest(ORMModel):
    reset_token: str = Field(min_length=20)
    otp_code: str = Field(min_length=4, max_length=10)
    new_password: str = Field(min_length=8, max_length=128)


class AccessTokenPayload(ORMModel):
    sub: UUID
    role: UserRole
    type: str


class MeResponse(CurrentUserResponse):
    pass
