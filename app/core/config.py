from decimal import Decimal
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True)

    PROJECT_NAME: str = "Property Backend API"
    APP_VERSION: str = "0.4.0"
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

    FIRST_SUPER_ADMIN_EMAIL: str = ""
    FIRST_SUPER_ADMIN_PASSWORD: str = ""
    FIRST_SUPER_ADMIN_FULL_NAME: str = ""

    PAYSTACK_PUBLIC_KEY: str = ""
    PAYSTACK_SECRET_KEY: str = ""
    PAYSTACK_WEBHOOK_SECRET: str = ""
    PAYSTACK_CURRENCY: str = "NGN"
    # Amount in major currency unit. Example: 10000 means ₦10,000; backend sends 1,000,000 kobo to Paystack.
    AGENT_VERIFICATION_FEE: Decimal = Decimal("0")
    PAYSTACK_CALLBACK_URL: str = ""
    PAYSTACK_BASE_URL: str = "https://api.paystack.co"

    MAX_CHAT_IMAGE_SIZE_MB: int = 5
    MAX_CHAT_VIDEO_SIZE_MB: int = 50

    @field_validator("ALLOWED_ORIGINS")
    @classmethod
    def clean_origins(cls, value: str) -> str:
        return ",".join(origin.strip() for origin in value.split(",") if origin.strip())

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
    def paystack_amount_minor_units(self) -> int:
        # Paystack expects amount in the smallest currency unit; NGN uses kobo.
        return int(self.AGENT_VERIFICATION_FEE * Decimal("100"))


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
