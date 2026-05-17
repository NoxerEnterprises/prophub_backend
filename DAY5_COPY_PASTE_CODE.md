# Day 5 Copy-Paste Code

This file contains all new/replaced files needed for Day 5 on top of the async Day 3 backend.

Manual steps:

1. Create Supabase Storage bucket `property-media` as public.
2. Ensure `.env` has `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `SUPABASE_STORAGE_BUCKET=property-media`.
3. Run `alembic upgrade head`.
4. For development until Paystack is integrated, run `python scripts/mark_agent_paid.py "<agent_profile_id>"`, then approve the agent through the admin API.


## `app/core/enums.py`

```python
from enum import StrEnum


class UserRole(StrEnum):
    USER = "USER"
    AGENT = "AGENT"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


class AgentStatus(StrEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DISABLED = "DISABLED"


class AdminAction(StrEnum):
    AGENT_APPROVED = "AGENT_APPROVED"
    AGENT_REJECTED = "AGENT_REJECTED"
    AGENT_DISABLED = "AGENT_DISABLED"
    AGENT_ENABLED = "AGENT_ENABLED"
    ADMIN_CREATED = "ADMIN_CREATED"
    PROPERTY_CREATED = "PROPERTY_CREATED"
    PROPERTY_UPDATED = "PROPERTY_UPDATED"
    PROPERTY_DELETED = "PROPERTY_DELETED"
    PROPERTY_MEDIA_UPLOADED = "PROPERTY_MEDIA_UPLOADED"
    PROPERTY_MEDIA_DELETED = "PROPERTY_MEDIA_DELETED"


class PropertyCategory(StrEnum):
    LAND = "LAND"
    HOUSE = "HOUSE"
    APARTMENT = "APARTMENT"
    COMMERCIAL = "COMMERCIAL"
    OFFICE = "OFFICE"
    SHOP = "SHOP"
    WAREHOUSE = "WAREHOUSE"


class ListingType(StrEnum):
    SALE = "SALE"
    RENT = "RENT"
    SHORTLET = "SHORTLET"


class PropertyStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    SOLD = "SOLD"
    RENTED = "RENTED"
    PENDING = "PENDING"
    HIDDEN = "HIDDEN"


class MediaType(StrEnum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class Environment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
```

## `app/models/property.py`

```python
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ListingType, PropertyCategory, PropertyStatus
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.agent_profile import AgentProfile
    from app.models.property_media import PropertyMedia


class Property(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "properties"
    __table_args__ = (
        Index("ix_properties_public_feed", "is_published", "deleted_at", "status"),
        Index("ix_properties_location", "country", "state", "local_government", "community"),
        Index("ix_properties_price", "price"),
    )

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 2), index=True, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="NGN", nullable=False)

    country: Mapped[str] = mapped_column(String(100), default="Nigeria", index=True, nullable=False)
    state: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    local_government: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    community: Mapped[str | None] = mapped_column(String(160), index=True, nullable=True)
    address_details: Mapped[str | None] = mapped_column(Text, nullable=True)

    category: Mapped[str] = mapped_column(String(40), default=PropertyCategory.LAND.value, index=True, nullable=False)
    listing_type: Mapped[str] = mapped_column(String(40), default=ListingType.SALE.value, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default=PropertyStatus.AVAILABLE.value, index=True, nullable=False)

    is_published: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True, nullable=True)

    agent: Mapped[AgentProfile] = relationship("AgentProfile", back_populates="properties", lazy="selectin")
    media: Mapped[list[PropertyMedia]] = relationship(
        "PropertyMedia",
        back_populates="property",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="PropertyMedia.position.asc(), PropertyMedia.created_at.asc()",
    )
```

## `app/models/property_media.py`

```python
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import MediaType
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.property import Property


class PropertyMedia(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "property_media"
    __table_args__ = (UniqueConstraint("property_id", "storage_path", name="uq_property_media_property_id_storage_path"),)

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    media_type: Mapped[str] = mapped_column(String(20), default=MediaType.IMAGE.value, index=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    property: Mapped[Property] = relationship("Property", back_populates="media", lazy="selectin")
```

## `app/models/agent_profile.py`

```python
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import AgentStatus
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.property import Property
    from app.models.user import User


class AgentProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    business_name: Mapped[str] = mapped_column(String(160), nullable=False)
    business_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    business_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    license_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(100), default="Nigeria", nullable=False)

    status: Mapped[str] = mapped_column(String(32), default=AgentStatus.PENDING.value, index=True, nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disabled_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="agent_profile", lazy="selectin", foreign_keys=[user_id])
    properties: Mapped[list[Property]] = relationship(
        "Property",
        back_populates="agent",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
```

## `app/models/__init__.py`

```python
from app.models.admin_activity_log import AdminActivityLog
from app.models.admin_profile import AdminProfile
from app.models.agent_profile import AgentProfile
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.user import User

__all__ = [
    "AdminActivityLog",
    "AdminProfile",
    "AgentProfile",
    "PasswordResetToken",
    "RefreshToken",
    "User",
]

from app.models.property import Property
from app.models.property_media import PropertyMedia
```

## `app/schemas/property.py`

```python
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, field_validator

from app.core.enums import ListingType, MediaType, PropertyCategory, PropertyStatus
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
```

## `app/repositories/property_repository.py`

```python
from __future__ import annotations

import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import AgentStatus, PropertyStatus
from app.models.agent_profile import AgentProfile
from app.models.property import Property
from app.models.property_media import PropertyMedia


class PropertyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, property_obj: Property) -> Property:
        self.session.add(property_obj)
        await self.session.flush()
        return property_obj

    async def add_media(self, media: PropertyMedia) -> PropertyMedia:
        self.session.add(media)
        await self.session.flush()
        return media

    async def get_by_id(self, property_id: uuid.UUID) -> Property | None:
        statement = (
            select(Property)
            .where(Property.id == property_id)
            .options(
                selectinload(Property.agent),
                selectinload(Property.media),
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_public_by_id(self, property_id: uuid.UUID) -> Property | None:
        statement = (
            select(Property)
            .join(Property.agent)
            .where(
                Property.id == property_id,
                Property.deleted_at.is_(None),
                Property.is_published.is_(True),
                Property.status != PropertyStatus.HIDDEN.value,
                AgentProfile.status == AgentStatus.APPROVED.value,
            )
            .options(
                selectinload(Property.agent),
                selectinload(Property.media),
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_agent_owned_property(self, property_id: uuid.UUID, agent_id: uuid.UUID) -> Property | None:
        statement = (
            select(Property)
            .where(Property.id == property_id, Property.agent_id == agent_id, Property.deleted_at.is_(None))
            .options(selectinload(Property.agent), selectinload(Property.media))
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_public(self, *, page: int = 1, limit: int = 20) -> tuple[list[Property], int]:
        filters = [
            Property.deleted_at.is_(None),
            Property.is_published.is_(True),
            Property.status != PropertyStatus.HIDDEN.value,
            AgentProfile.status == AgentStatus.APPROVED.value,
        ]
        base_statement = select(Property).join(Property.agent).where(and_(*filters))
        count_statement = select(func.count()).select_from(base_statement.subquery())
        count_result = await self.session.execute(count_statement)
        total = int(count_result.scalar_one() or 0)

        statement = (
            base_statement.options(selectinload(Property.agent), selectinload(Property.media))
            .order_by(Property.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().unique().all()), total

    async def list_by_agent(self, *, agent_id: uuid.UUID, page: int = 1, limit: int = 20) -> tuple[list[Property], int]:
        base_statement = select(Property).where(Property.agent_id == agent_id, Property.deleted_at.is_(None))
        count_statement = select(func.count()).select_from(base_statement.subquery())
        count_result = await self.session.execute(count_statement)
        total = int(count_result.scalar_one() or 0)

        statement = (
            base_statement.options(selectinload(Property.agent), selectinload(Property.media))
            .order_by(Property.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().unique().all()), total

    async def count_media(self, property_id: uuid.UUID) -> int:
        statement = select(func.count()).select_from(PropertyMedia).where(PropertyMedia.property_id == property_id)
        result = await self.session.execute(statement)
        return int(result.scalar_one() or 0)

    async def get_media_by_id(self, media_id: uuid.UUID) -> PropertyMedia | None:
        statement = select(PropertyMedia).where(PropertyMedia.id == media_id).options(selectinload(PropertyMedia.property))
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_owned_media(self, *, media_id: uuid.UUID, property_id: uuid.UUID, agent_id: uuid.UUID) -> PropertyMedia | None:
        statement = (
            select(PropertyMedia)
            .join(PropertyMedia.property)
            .where(PropertyMedia.id == media_id, PropertyMedia.property_id == property_id, Property.agent_id == agent_id)
            .options(selectinload(PropertyMedia.property))
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def delete_media_record(self, media: PropertyMedia) -> None:
        await self.session.delete(media)
        await self.session.flush()
```

## `app/services/storage_service.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import httpx
from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import BadRequestError


@dataclass(frozen=True)
class UploadedStorageObject:
    path: str
    public_url: str
    content_type: str
    size_bytes: int


class SupabaseStorageService:
    allowed_image_content_types = {"image/jpeg", "image/png", "image/webp"}
    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    max_image_size_bytes = 5 * 1024 * 1024

    def __init__(self) -> None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            raise BadRequestError("Supabase storage credentials are not configured")
        self.base_url = settings.SUPABASE_URL.rstrip("/")
        self.bucket = settings.SUPABASE_STORAGE_BUCKET
        self.headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        }

    async def upload_public_image(self, *, file: UploadFile, path: str) -> UploadedStorageObject:
        content_type = file.content_type or ""
        extension = Path(file.filename or "").suffix.lower()

        if content_type not in self.allowed_image_content_types:
            raise BadRequestError("Only JPEG, PNG, and WEBP images are allowed")
        if extension not in self.allowed_extensions:
            raise BadRequestError("Only .jpg, .jpeg, .png, and .webp files are allowed")

        file_bytes = await file.read()
        size = len(file_bytes)
        if size == 0:
            raise BadRequestError("Uploaded file is empty")
        if size > self.max_image_size_bytes:
            raise BadRequestError("Image size must not exceed 5 MB")

        encoded_path = self._encode_path(path)
        url = f"{self.base_url}/storage/v1/object/{self.bucket}/{encoded_path}"
        headers = {
            **self.headers,
            "Content-Type": content_type,
            "Cache-Control": "3600",
            "x-upsert": "false",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, content=file_bytes)

        if response.status_code not in {200, 201}:
            raise BadRequestError("Supabase Storage upload failed", details=response.text)

        return UploadedStorageObject(
            path=path,
            public_url=self.get_public_url(path),
            content_type=content_type,
            size_bytes=size,
        )

    async def delete_object(self, path: str) -> None:
        encoded_path = self._encode_path(path)
        url = f"{self.base_url}/storage/v1/object/{self.bucket}/{encoded_path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(url, headers=self.headers)

        if response.status_code not in {200, 204, 404}:
            raise BadRequestError("Supabase Storage delete failed", details=response.text)

    def get_public_url(self, path: str) -> str:
        return f"{self.base_url}/storage/v1/object/public/{self.bucket}/{self._encode_path(path)}"

    @staticmethod
    def _encode_path(path: str) -> str:
        return "/".join(quote(part, safe="") for part in path.split("/"))
```

## `app/services/property_service.py`

```python
from __future__ import annotations

import uuid
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AdminAction, MediaType, PropertyStatus
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.security import now_utc
from app.models.agent_profile import AgentProfile
from app.models.property import Property
from app.models.property_media import PropertyMedia
from app.models.user import User
from app.repositories.property_repository import PropertyRepository
from app.schemas.property import PropertyCreate, PropertyUpdate
from app.services.admin_activity_service import AdminActivityService
from app.services.storage_service import SupabaseStorageService


class PropertyService:
    max_images_per_property = 10

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.properties = PropertyRepository(session)
        self.activity = AdminActivityService(session)

    async def create_property(self, *, agent: AgentProfile, payload: PropertyCreate) -> Property:
        property_obj = Property(
            agent_id=agent.id,
            title=payload.title,
            description=payload.description,
            price=payload.price,
            currency=payload.currency,
            country=payload.country,
            state=payload.state,
            local_government=payload.local_government,
            community=payload.community,
            address_details=payload.address_details,
            category=payload.category.value,
            listing_type=payload.listing_type.value,
            status=payload.status.value,
            is_published=payload.is_published,
        )
        await self.properties.add(property_obj)
        await self.session.commit()
        await self.session.refresh(property_obj, attribute_names=["agent", "media"])
        return property_obj

    async def list_public_properties(self, *, page: int = 1, limit: int = 20) -> tuple[list[Property], int]:
        return await self.properties.list_public(page=page, limit=limit)

    async def get_public_property(self, property_id: UUID) -> Property:
        property_obj = await self.properties.get_public_by_id(property_id)
        if not property_obj:
            raise NotFoundError("Property not found")
        return property_obj

    async def list_my_properties(self, *, agent: AgentProfile, page: int = 1, limit: int = 20) -> tuple[list[Property], int]:
        return await self.properties.list_by_agent(agent_id=agent.id, page=page, limit=limit)

    async def get_my_property(self, *, property_id: UUID, agent: AgentProfile) -> Property:
        property_obj = await self.properties.get_agent_owned_property(property_id, agent.id)
        if not property_obj:
            raise NotFoundError("Property not found")
        return property_obj

    async def update_my_property(self, *, property_id: UUID, agent: AgentProfile, payload: PropertyUpdate) -> Property:
        property_obj = await self.get_my_property(property_id=property_id, agent=agent)
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field in {"category", "listing_type", "status"} and value is not None:
                value = value.value
            setattr(property_obj, field, value)
        await self.session.commit()
        await self.session.refresh(property_obj, attribute_names=["agent", "media"])
        return property_obj

    async def soft_delete_my_property(self, *, property_id: UUID, agent: AgentProfile) -> None:
        property_obj = await self.get_my_property(property_id=property_id, agent=agent)
        property_obj.deleted_at = now_utc()
        property_obj.is_published = False
        await self.session.commit()

    async def upload_property_image(self, *, property_id: UUID, agent: AgentProfile, file: UploadFile, position: int = 0) -> PropertyMedia:
        property_obj = await self.get_my_property(property_id=property_id, agent=agent)
        if property_obj.status == PropertyStatus.HIDDEN.value:
            raise ForbiddenError("Cannot upload media to a hidden property")

        current_media_count = await self.properties.count_media(property_id)
        if current_media_count >= self.max_images_per_property:
            raise BadRequestError(f"A property can have at most {self.max_images_per_property} images")

        extension = Path(file.filename or "").suffix.lower()
        storage_path = f"properties/{property_id}/{uuid.uuid4()}{extension}"
        storage_object = await SupabaseStorageService().upload_public_image(file=file, path=storage_path)

        media = PropertyMedia(
            property_id=property_id,
            file_url=storage_object.public_url,
            storage_path=storage_object.path,
            media_type=MediaType.IMAGE.value,
            content_type=storage_object.content_type,
            file_size_bytes=storage_object.size_bytes,
            position=position,
        )
        await self.properties.add_media(media)
        await self.session.commit()
        await self.session.refresh(media)
        return media

    async def delete_property_image(self, *, property_id: UUID, media_id: UUID, agent: AgentProfile) -> None:
        media = await self.properties.get_owned_media(media_id=media_id, property_id=property_id, agent_id=agent.id)
        if not media:
            raise NotFoundError("Property media not found")

        await SupabaseStorageService().delete_object(media.storage_path)
        await self.properties.delete_media_record(media)
        await self.session.commit()

    async def log_property_action(self, *, admin: User, action: AdminAction, property_obj: Property, note: str | None = None) -> None:
        await self.activity.log(
            admin_id=admin.id,
            action=action.value,
            target_type="property",
            target_id=property_obj.id,
            description=note,
            metadata={"property_id": str(property_obj.id)},
        )
```

## `app/api/v1/routes/properties.py`

```python
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.api.dependencies import CurrentUserDep, SessionDep, require_approved_agent
from app.models.agent_profile import AgentProfile
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.schemas.property import PropertyCreate, PropertyMediaResponse, PropertyResponse, PropertyUpdate
from app.services.agent_service import AgentService
from app.services.property_service import PropertyService

router = APIRouter(prefix="/properties", tags=["Properties"])
ApprovedAgentDep = Annotated[User, Depends(require_approved_agent)]


async def _approved_agent_profile(current_user: User, session: SessionDep) -> AgentProfile:
    return await AgentService(session).get_my_agent_profile(current_user)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=APIResponse[PropertyResponse])
async def create_property(
    payload: PropertyCreate,
    current_user: ApprovedAgentDep,
    session: SessionDep,
) -> APIResponse[PropertyResponse]:
    agent = await _approved_agent_profile(current_user, session)
    property_obj = await PropertyService(session).create_property(agent=agent, payload=payload)
    return APIResponse(message="Property created", data=PropertyResponse.model_validate(property_obj))


@router.get("", response_model=APIResponse[PaginatedResponse[PropertyResponse]])
async def list_public_properties(
    session: SessionDep,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> APIResponse[PaginatedResponse[PropertyResponse]]:
    properties, total = await PropertyService(session).list_public_properties(page=page, limit=limit)
    return APIResponse(
        message="Properties retrieved",
        data=PaginatedResponse(
            items=[PropertyResponse.model_validate(property_obj) for property_obj in properties],
            meta=PaginationMeta(page=page, limit=limit, total=total),
        ),
    )


@router.get("/{property_id}", response_model=APIResponse[PropertyResponse])
async def get_public_property(property_id: UUID, session: SessionDep) -> APIResponse[PropertyResponse]:
    property_obj = await PropertyService(session).get_public_property(property_id)
    return APIResponse(message="Property retrieved", data=PropertyResponse.model_validate(property_obj))


@router.patch("/{property_id}", response_model=APIResponse[PropertyResponse])
async def update_property(
    property_id: UUID,
    payload: PropertyUpdate,
    current_user: ApprovedAgentDep,
    session: SessionDep,
) -> APIResponse[PropertyResponse]:
    agent = await _approved_agent_profile(current_user, session)
    property_obj = await PropertyService(session).update_my_property(property_id=property_id, agent=agent, payload=payload)
    return APIResponse(message="Property updated", data=PropertyResponse.model_validate(property_obj))


@router.delete("/{property_id}", response_model=APIResponse[dict[str, bool]])
async def delete_property(
    property_id: UUID,
    current_user: ApprovedAgentDep,
    session: SessionDep,
) -> APIResponse[dict[str, bool]]:
    agent = await _approved_agent_profile(current_user, session)
    await PropertyService(session).soft_delete_my_property(property_id=property_id, agent=agent)
    return APIResponse(message="Property deleted", data={"deleted": True})


@router.post("/{property_id}/media", status_code=status.HTTP_201_CREATED, response_model=APIResponse[PropertyMediaResponse])
async def upload_property_image(
    property_id: UUID,
    current_user: ApprovedAgentDep,
    session: SessionDep,
    file: UploadFile = File(...),
    position: int = Query(default=0, ge=0),
) -> APIResponse[PropertyMediaResponse]:
    agent = await _approved_agent_profile(current_user, session)
    media = await PropertyService(session).upload_property_image(property_id=property_id, agent=agent, file=file, position=position)
    return APIResponse(message="Property image uploaded", data=PropertyMediaResponse.model_validate(media))


@router.delete("/{property_id}/media/{media_id}", response_model=APIResponse[dict[str, bool]])
async def delete_property_image(
    property_id: UUID,
    media_id: UUID,
    current_user: ApprovedAgentDep,
    session: SessionDep,
) -> APIResponse[dict[str, bool]]:
    agent = await _approved_agent_profile(current_user, session)
    await PropertyService(session).delete_property_image(property_id=property_id, media_id=media_id, agent=agent)
    return APIResponse(message="Property image deleted", data={"deleted": True})
```

## `app/api/v1/routes/agent_properties.py`

```python
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import SessionDep, require_approved_agent
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.schemas.property import PropertyResponse
from app.services.agent_service import AgentService
from app.services.property_service import PropertyService

router = APIRouter(prefix="/agents/me/properties", tags=["Agent Properties"])
ApprovedAgentDep = Annotated[User, Depends(require_approved_agent)]


@router.get("", response_model=APIResponse[PaginatedResponse[PropertyResponse]])
async def list_my_properties(
    current_user: ApprovedAgentDep,
    session: SessionDep,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> APIResponse[PaginatedResponse[PropertyResponse]]:
    agent = await AgentService(session).get_my_agent_profile(current_user)
    properties, total = await PropertyService(session).list_my_properties(agent=agent, page=page, limit=limit)
    return APIResponse(
        message="Agent properties retrieved",
        data=PaginatedResponse(
            items=[PropertyResponse.model_validate(property_obj) for property_obj in properties],
            meta=PaginationMeta(page=page, limit=limit, total=total),
        ),
    )
```

## `app/api/v1/router.py`

```python
from fastapi import APIRouter

from app.api.v1.routes import admin, agent_properties, agents, auth, health, properties

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(agents.router)
api_router.include_router(agent_properties.router)
api_router.include_router(properties.router)
api_router.include_router(admin.router)
```

## `migrations/versions/0002_add_properties_and_media.py`

```python
"""add properties and property media

Revision ID: 0002_add_properties_and_media
Revises: 0001_create_async_day3_core
Create Date: 2026-05-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_add_properties_and_media"
down_revision = "0001_create_async_day3_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "properties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("price", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="NGN"),
        sa.Column("country", sa.String(length=100), nullable=False, server_default="Nigeria"),
        sa.Column("state", sa.String(length=100), nullable=False),
        sa.Column("local_government", sa.String(length=120), nullable=True),
        sa.Column("community", sa.String(length=160), nullable=True),
        sa.Column("address_details", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("listing_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="AVAILABLE"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_profiles.id"], ondelete="CASCADE", name="fk_properties_agent_id_agent_profiles"),
    )
    op.create_index("ix_properties_agent_id", "properties", ["agent_id"])
    op.create_index("ix_properties_title", "properties", ["title"])
    op.create_index("ix_properties_price", "properties", ["price"])
    op.create_index("ix_properties_country", "properties", ["country"])
    op.create_index("ix_properties_state", "properties", ["state"])
    op.create_index("ix_properties_local_government", "properties", ["local_government"])
    op.create_index("ix_properties_community", "properties", ["community"])
    op.create_index("ix_properties_category", "properties", ["category"])
    op.create_index("ix_properties_listing_type", "properties", ["listing_type"])
    op.create_index("ix_properties_status", "properties", ["status"])
    op.create_index("ix_properties_is_published", "properties", ["is_published"])
    op.create_index("ix_properties_deleted_at", "properties", ["deleted_at"])
    op.create_index("ix_properties_public_feed", "properties", ["is_published", "deleted_at", "status"])
    op.create_index("ix_properties_location", "properties", ["country", "state", "local_government", "community"])

    op.create_table(
        "property_media",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("media_type", sa.String(length=20), nullable=False, server_default="IMAGE"),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE", name="fk_property_media_property_id_properties"),
        sa.UniqueConstraint("property_id", "storage_path", name="uq_property_media_property_id_storage_path"),
    )
    op.create_index("ix_property_media_property_id", "property_media", ["property_id"])
    op.create_index("ix_property_media_media_type", "property_media", ["media_type"])


def downgrade() -> None:
    op.drop_table("property_media")
    op.drop_table("properties")
```

## `scripts/mark_agent_paid.py`

```python
from __future__ import annotations

import asyncio
import sys
from uuid import UUID

from sqlalchemy import select

from app.core.enums import AgentStatus
from app.db.session import AsyncSessionLocal
from app.models.agent_profile import AgentProfile


async def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python scripts/mark_agent_paid.py "<agent_profile_id>"')
        raise SystemExit(1)

    agent_id = UUID(sys.argv[1])
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AgentProfile).where(AgentProfile.id == agent_id))
        agent = result.scalar_one_or_none()
        if not agent:
            print("Agent not found")
            raise SystemExit(1)

        agent.previous_status = agent.status
        agent.status = AgentStatus.PAID.value
        agent.status_note = "Manually marked as PAID for development testing before Paystack integration."
        await session.commit()
        print(f"Agent {agent.id} marked as PAID.")


if __name__ == "__main__":
    asyncio.run(main())
```
