from decimal import Decimal
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True)

    PROJECT_NAME: str = "ProHub Backend API"
    APP_VERSION: str = "0.7.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:8081"

    DATABASE_URL: Annotated[str, Field(min_length=1)]

    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "property-media"

    JWT_SECRET_KEY: Annotated[str, Field(min_length=32)]
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    PASSWORD_RESET_EXPIRE_MINUTES: int = 15
    PASSWORD_RESET_OTP_LENGTH: int = 6
    EMAIL_VERIFICATION_EXPIRE_MINUTES: int = 15
    EMAIL_VERIFICATION_OTP_LENGTH: int = 6

    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "ProHub <noreply@example.com>"
    FRONTEND_EMAIL_VERIFY_URL: str = ""

    FIRST_SUPER_ADMIN_EMAIL: str = ""
    FIRST_SUPER_ADMIN_PASSWORD: str = ""
    FIRST_SUPER_ADMIN_FULL_NAME: str = ""

    PAYSTACK_PUBLIC_KEY: str = ""
    PAYSTACK_SECRET_KEY: str = ""
    PAYSTACK_WEBHOOK_SECRET: str = ""
    PAYSTACK_CURRENCY: str = "NGN"
    PAYSTACK_CALLBACK_URL: str = ""
    PAYSTACK_BASE_URL: str = "https://api.paystack.co"
    AGENT_SUBSCRIPTION_FEE: Decimal = Decimal("0")
    AGENT_VERIFICATION_FEE: Decimal = Decimal("0")  # Legacy fallback.
    SUBSCRIPTION_DURATION_MONTHS: int = 12

    NOXER_CONTACT_USER_ID: str = ""

    MAX_PROPERTY_IMAGE_SIZE_MB: int = 5
    MAX_CHAT_IMAGE_SIZE_MB: int = 5
    MAX_CHAT_VIDEO_SIZE_MB: int = 50
    MAX_DOCUMENT_SIZE_MB: int = 10

    @field_validator("ALLOWED_ORIGINS")
    @classmethod
    def clean_origins(cls, value: str) -> str:
        return ",".join(origin.strip() for origin in value.split(",") if origin.strip())

    @field_validator("SUBSCRIPTION_DURATION_MONTHS")
    @classmethod
    def validate_subscription_duration(cls, value: int) -> int:
        if value < 1 or value > 12:
            raise ValueError("SUBSCRIPTION_DURATION_MONTHS must be any integer from 1 to 12")
        return value

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL.strip()
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def agent_subscription_fee(self) -> Decimal:
        return self.AGENT_SUBSCRIPTION_FEE if self.AGENT_SUBSCRIPTION_FEE > 0 else self.AGENT_VERIFICATION_FEE

    @property
    def paystack_amount_minor_units(self) -> int:
        return int(self.agent_subscription_fee * Decimal("100"))


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
