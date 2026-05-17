from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, field_validator

from app.core.enums import ListingType, MediaType, PropertyCategory, PropertySort, PropertyStatus
from app.schemas.common import ORMModel


class PropertyAgentSummary(ORMModel):
    id: UUID
    business_name: str
    business_phone: str | None = None
    business_email: str | None = None
    city: str | None = None
    state: str | None = None
    country: str
    status: str


class PropertyMediaResponse(ORMModel):
    id: UUID
    property_id: UUID
    file_url: str
    storage_path: str
    media_type: MediaType
    content_type: str
    file_size_bytes: int
    position: int
    created_at: datetime
    updated_at: datetime


class PropertyBase(ORMModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    price: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str = Field(default="NGN", min_length=3, max_length=3)
    country: str = Field(default="Nigeria", min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    local_government: str | None = Field(default=None, max_length=120)
    community: str | None = Field(default=None, max_length=160)
    address_details: str | None = Field(default=None, max_length=1000)
    category: PropertyCategory
    listing_type: ListingType
    status: PropertyStatus = PropertyStatus.AVAILABLE
    is_published: bool = True

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper().strip()

    @field_validator("title", "description", "country", "state", "local_government", "community", "address_details", mode="before")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip()


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(ORMModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=10, max_length=5000)
    price: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    country: str | None = Field(default=None, min_length=2, max_length=100)
    state: str | None = Field(default=None, min_length=2, max_length=100)
    local_government: str | None = Field(default=None, max_length=120)
    community: str | None = Field(default=None, max_length=160)
    address_details: str | None = Field(default=None, max_length=1000)
    category: PropertyCategory | None = None
    listing_type: ListingType | None = None
    status: PropertyStatus | None = None
    is_published: bool | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper().strip() if value else value

    @field_validator("title", "description", "country", "state", "local_government", "community", "address_details", mode="before")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip()


class PropertyResponse(ORMModel):
    id: UUID
    agent_id: UUID
    title: str
    description: str
    price: Decimal
    currency: str
    country: str
    state: str
    local_government: str | None = None
    community: str | None = None
    address_details: str | None = None
    category: PropertyCategory
    listing_type: ListingType
    status: PropertyStatus
    is_published: bool
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    media: list[PropertyMediaResponse] = []
    agent: PropertyAgentSummary | None = None


class PropertySearchQuery(ORMModel):
    q: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    local_government: str | None = Field(default=None, max_length=120)
    community: str | None = Field(default=None, max_length=160)
    min_price: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    max_price: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    category: PropertyCategory | None = None
    listing_type: ListingType | None = None
    status: PropertyStatus | None = None
    sort: PropertySort = PropertySort.NEWEST


class AdminPropertyListQuery(PropertySearchQuery):
    agent_id: UUID | None = None
    include_deleted: bool = False


class AdminPropertyStatusRequest(ORMModel):
    note: str | None = Field(default=None, max_length=1000)


class AdminPropertyRestoreRequest(AdminPropertyStatusRequest):
    status: PropertyStatus = PropertyStatus.AVAILABLE
    is_published: bool = True
