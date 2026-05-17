# Day 6 Copy-Paste Code

This document contains every new or replaced file required for Day 6. The ZIP package already contains these files in the correct locations. Use this file only if you want to manually patch another codebase.


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
    PROPERTY_HIDDEN = "PROPERTY_HIDDEN"
    PROPERTY_RESTORED = "PROPERTY_RESTORED"
    PROPERTY_ADMIN_DELETED = "PROPERTY_ADMIN_DELETED"


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


class PropertySort(StrEnum):
    NEWEST = "newest"
    OLDEST = "oldest"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"


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


## `app/schemas/property.py`

```python
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

```


## `app/repositories/property_repository.py`

```python
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import and_, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

from app.core.enums import AgentStatus, ListingType, PropertyCategory, PropertySort, PropertyStatus
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

    async def get_admin_by_id(self, property_id: uuid.UUID) -> Property | None:
        statement = (
            select(Property)
            .where(Property.id == property_id)
            .options(
                selectinload(Property.agent).selectinload(AgentProfile.user),
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
        return await self.search_public(page=page, limit=limit)

    async def search_public(
        self,
        *,
        page: int = 1,
        limit: int = 20,
        q: str | None = None,
        country: str | None = None,
        state: str | None = None,
        local_government: str | None = None,
        community: str | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        category: PropertyCategory | None = None,
        listing_type: ListingType | None = None,
        status: PropertyStatus | None = None,
        sort: PropertySort = PropertySort.NEWEST,
    ) -> tuple[list[Property], int]:
        filters = [
            Property.deleted_at.is_(None),
            Property.is_published.is_(True),
            Property.status != PropertyStatus.HIDDEN.value,
            AgentProfile.status == AgentStatus.APPROVED.value,
        ]
        base_statement = select(Property).join(Property.agent)
        base_statement = self._apply_property_filters(
            base_statement,
            filters=filters,
            q=q,
            country=country,
            state=state,
            local_government=local_government,
            community=community,
            min_price=min_price,
            max_price=max_price,
            category=category,
            listing_type=listing_type,
            status=status,
        )
        return await self._paginate_properties(base_statement=base_statement, page=page, limit=limit, sort=sort)

    async def list_by_agent(self, *, agent_id: uuid.UUID, page: int = 1, limit: int = 20) -> tuple[list[Property], int]:
        base_statement = select(Property).where(Property.agent_id == agent_id, Property.deleted_at.is_(None))
        return await self._paginate_properties(base_statement=base_statement, page=page, limit=limit, sort=PropertySort.NEWEST)

    async def list_for_admin(
        self,
        *,
        page: int = 1,
        limit: int = 20,
        q: str | None = None,
        country: str | None = None,
        state: str | None = None,
        local_government: str | None = None,
        community: str | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        category: PropertyCategory | None = None,
        listing_type: ListingType | None = None,
        status: PropertyStatus | None = None,
        sort: PropertySort = PropertySort.NEWEST,
        agent_id: uuid.UUID | None = None,
        include_deleted: bool = False,
    ) -> tuple[list[Property], int]:
        filters = []
        if not include_deleted:
            filters.append(Property.deleted_at.is_(None))
        if agent_id is not None:
            filters.append(Property.agent_id == agent_id)

        base_statement = select(Property).join(Property.agent)
        base_statement = self._apply_property_filters(
            base_statement,
            filters=filters,
            q=q,
            country=country,
            state=state,
            local_government=local_government,
            community=community,
            min_price=min_price,
            max_price=max_price,
            category=category,
            listing_type=listing_type,
            status=status,
        )
        return await self._paginate_properties(base_statement=base_statement, page=page, limit=limit, sort=sort)

    def _apply_property_filters(
        self,
        base_statement: Select[tuple[Property]],
        *,
        filters: list,
        q: str | None,
        country: str | None,
        state: str | None,
        local_government: str | None,
        community: str | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
        category: PropertyCategory | None,
        listing_type: ListingType | None,
        status: PropertyStatus | None,
    ) -> Select[tuple[Property]]:
        if q:
            q_clean = q.strip()
            if q_clean:
                pattern = f"%{q_clean}%"
                search_text = (
                    func.coalesce(Property.title, "")
                    + literal(" ")
                    + func.coalesce(Property.description, "")
                    + literal(" ")
                    + func.coalesce(Property.country, "")
                    + literal(" ")
                    + func.coalesce(Property.state, "")
                    + literal(" ")
                    + func.coalesce(Property.local_government, "")
                    + literal(" ")
                    + func.coalesce(Property.community, "")
                )
                search_vector = func.to_tsvector("simple", search_text)
                search_query = func.plainto_tsquery("simple", q_clean)
                filters.append(
                    or_(
                        search_vector.op("@@")(search_query),
                        Property.title.ilike(pattern),
                        Property.description.ilike(pattern),
                        Property.state.ilike(pattern),
                        Property.local_government.ilike(pattern),
                        Property.community.ilike(pattern),
                    )
                )
        if country:
            filters.append(Property.country.ilike(country.strip()))
        if state:
            filters.append(Property.state.ilike(state.strip()))
        if local_government:
            filters.append(Property.local_government.ilike(local_government.strip()))
        if community:
            filters.append(Property.community.ilike(community.strip()))
        if min_price is not None:
            filters.append(Property.price >= min_price)
        if max_price is not None:
            filters.append(Property.price <= max_price)
        if category is not None:
            filters.append(Property.category == category.value)
        if listing_type is not None:
            filters.append(Property.listing_type == listing_type.value)
        if status is not None:
            filters.append(Property.status == status.value)

        if filters:
            base_statement = base_statement.where(and_(*filters))
        return base_statement

    async def _paginate_properties(
        self,
        *,
        base_statement: Select[tuple[Property]],
        page: int,
        limit: int,
        sort: PropertySort,
    ) -> tuple[list[Property], int]:
        count_statement = select(func.count()).select_from(base_statement.subquery())
        count_result = await self.session.execute(count_statement)
        total = int(count_result.scalar_one() or 0)

        statement = (
            self._apply_sort(base_statement, sort)
            .options(selectinload(Property.agent), selectinload(Property.media))
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().unique().all()), total

    def _apply_sort(self, statement: Select[tuple[Property]], sort: PropertySort) -> Select[tuple[Property]]:
        if sort == PropertySort.OLDEST:
            return statement.order_by(Property.created_at.asc())
        if sort == PropertySort.PRICE_ASC:
            return statement.order_by(Property.price.asc(), Property.created_at.desc())
        if sort == PropertySort.PRICE_DESC:
            return statement.order_by(Property.price.desc(), Property.created_at.desc())
        return statement.order_by(Property.created_at.desc())

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


## `app/services/property_service.py`

```python
from __future__ import annotations

import uuid
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AdminAction, MediaType, PropertyCategory, PropertySort, PropertyStatus, ListingType
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

    async def search_public_properties(
        self,
        *,
        page: int = 1,
        limit: int = 20,
        q: str | None = None,
        country: str | None = None,
        state: str | None = None,
        local_government: str | None = None,
        community: str | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        category: PropertyCategory | None = None,
        listing_type: ListingType | None = None,
        status: PropertyStatus | None = None,
        sort: PropertySort = PropertySort.NEWEST,
    ) -> tuple[list[Property], int]:
        self._validate_price_range(min_price=min_price, max_price=max_price)
        return await self.properties.search_public(
            page=page,
            limit=limit,
            q=q,
            country=country,
            state=state,
            local_government=local_government,
            community=community,
            min_price=min_price,
            max_price=max_price,
            category=category,
            listing_type=listing_type,
            status=status,
            sort=sort,
        )

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

    async def list_admin_properties(
        self,
        *,
        page: int = 1,
        limit: int = 20,
        q: str | None = None,
        country: str | None = None,
        state: str | None = None,
        local_government: str | None = None,
        community: str | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        category: PropertyCategory | None = None,
        listing_type: ListingType | None = None,
        status: PropertyStatus | None = None,
        sort: PropertySort = PropertySort.NEWEST,
        agent_id: UUID | None = None,
        include_deleted: bool = False,
    ) -> tuple[list[Property], int]:
        self._validate_price_range(min_price=min_price, max_price=max_price)
        return await self.properties.list_for_admin(
            page=page,
            limit=limit,
            q=q,
            country=country,
            state=state,
            local_government=local_government,
            community=community,
            min_price=min_price,
            max_price=max_price,
            category=category,
            listing_type=listing_type,
            status=status,
            sort=sort,
            agent_id=agent_id,
            include_deleted=include_deleted,
        )

    async def get_admin_property(self, property_id: UUID) -> Property:
        property_obj = await self.properties.get_admin_by_id(property_id)
        if not property_obj:
            raise NotFoundError("Property not found")
        return property_obj

    async def hide_property_for_admin(self, *, property_id: UUID, admin: User, note: str | None = None) -> Property:
        property_obj = await self.get_admin_property(property_id)
        if property_obj.deleted_at is not None:
            raise BadRequestError("Cannot hide a deleted property")
        if property_obj.status == PropertyStatus.HIDDEN.value:
            raise BadRequestError("Property is already hidden")

        property_obj.status = PropertyStatus.HIDDEN.value
        property_obj.is_published = False
        await self.log_property_action(
            admin=admin,
            action=AdminAction.PROPERTY_HIDDEN,
            property_obj=property_obj,
            note=note or "Property hidden by admin",
        )
        await self.session.commit()
        await self.session.refresh(property_obj, attribute_names=["agent", "media"])
        return property_obj

    async def restore_property_for_admin(
        self,
        *,
        property_id: UUID,
        admin: User,
        status: PropertyStatus = PropertyStatus.AVAILABLE,
        is_published: bool = True,
        note: str | None = None,
    ) -> Property:
        if status == PropertyStatus.HIDDEN:
            raise BadRequestError("Restore status cannot be HIDDEN")
        property_obj = await self.get_admin_property(property_id)
        if property_obj.deleted_at is not None:
            raise BadRequestError("Cannot restore a deleted property with this endpoint")

        property_obj.status = status.value
        property_obj.is_published = is_published
        await self.log_property_action(
            admin=admin,
            action=AdminAction.PROPERTY_RESTORED,
            property_obj=property_obj,
            note=note or "Property restored by admin",
        )
        await self.session.commit()
        await self.session.refresh(property_obj, attribute_names=["agent", "media"])
        return property_obj

    async def soft_delete_property_for_admin(self, *, property_id: UUID, admin: User, note: str | None = None) -> None:
        property_obj = await self.get_admin_property(property_id)
        if property_obj.deleted_at is not None:
            raise BadRequestError("Property is already deleted")
        property_obj.deleted_at = now_utc()
        property_obj.is_published = False
        await self.log_property_action(
            admin=admin,
            action=AdminAction.PROPERTY_ADMIN_DELETED,
            property_obj=property_obj,
            note=note or "Property deleted by admin",
        )
        await self.session.commit()

    async def log_property_action(self, *, admin: User, action: AdminAction, property_obj: Property, note: str | None = None) -> None:
        await self.activity.log(
            admin_id=admin.id,
            action=action.value,
            target_type="property",
            target_id=property_obj.id,
            description=note,
            metadata={
                "property_id": str(property_obj.id),
                "agent_id": str(property_obj.agent_id),
                "status": property_obj.status,
                "is_published": property_obj.is_published,
            },
        )

    def _validate_price_range(self, *, min_price: Decimal | None, max_price: Decimal | None) -> None:
        if min_price is not None and max_price is not None and min_price > max_price:
            raise BadRequestError("min_price cannot be greater than max_price")

```


## `app/api/v1/routes/properties.py`

```python
from __future__ import annotations

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.api.dependencies import SessionDep, require_approved_agent
from app.core.enums import ListingType, PropertyCategory, PropertySort, PropertyStatus
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


@router.get("/search", response_model=APIResponse[PaginatedResponse[PropertyResponse]])
async def search_public_properties(
    session: SessionDep,
    q: str | None = Query(default=None, max_length=100),
    country: str | None = Query(default=None, max_length=100),
    state: str | None = Query(default=None, max_length=100),
    local_government: str | None = Query(default=None, max_length=120),
    community: str | None = Query(default=None, max_length=160),
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    category: PropertyCategory | None = Query(default=None),
    listing_type: ListingType | None = Query(default=None),
    property_status: PropertyStatus | None = Query(default=None, alias="status"),
    sort: PropertySort = Query(default=PropertySort.NEWEST),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> APIResponse[PaginatedResponse[PropertyResponse]]:
    properties, total = await PropertyService(session).search_public_properties(
        page=page,
        limit=limit,
        q=q,
        country=country,
        state=state,
        local_government=local_government,
        community=community,
        min_price=min_price,
        max_price=max_price,
        category=category,
        listing_type=listing_type,
        status=property_status,
        sort=sort,
    )
    return APIResponse(
        message="Properties search completed",
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


## `app/api/v1/routes/admin.py`

```python
from __future__ import annotations

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import SessionDep, require_admin
from app.core.enums import AgentStatus, ListingType, PropertyCategory, PropertySort, PropertyStatus
from app.models.user import User
from app.repositories.admin_repository import AdminRepository
from app.schemas.admin import AdminActivityLogResponse
from app.schemas.agent import AgentAdminResponse, AgentApproveRequest, AgentStatusChangeRequest
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.schemas.property import AdminPropertyRestoreRequest, AdminPropertyStatusRequest, PropertyResponse
from app.services.agent_service import AgentService
from app.services.property_service import PropertyService

router = APIRouter(prefix="/admin", tags=["Admin"])

AdminDep = Annotated[User, Depends(require_admin)]


@router.get("/agents", response_model=APIResponse[PaginatedResponse[AgentAdminResponse]])
async def list_agents(
    session: SessionDep,
    _admin: AdminDep,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    status: AgentStatus | None = Query(default=None),
    q: str | None = Query(default=None, max_length=100),
) -> APIResponse[PaginatedResponse[AgentAdminResponse]]:
    agents, total = await AgentService(session).list_agents(page=page, limit=limit, status=status, q=q)
    items = [AgentAdminResponse.model_validate(agent) for agent in agents]
    return APIResponse(
        message="Agents retrieved",
        data=PaginatedResponse(items=items, meta=PaginationMeta(page=page, limit=limit, total=total)),
    )


@router.get("/agents/{agent_id}", response_model=APIResponse[AgentAdminResponse])
async def get_agent(agent_id: UUID, session: SessionDep, _admin: AdminDep) -> APIResponse[AgentAdminResponse]:
    agent = await AgentService(session).get_agent_for_admin(agent_id)
    return APIResponse(message="Agent retrieved", data=AgentAdminResponse.model_validate(agent))


@router.patch("/agents/{agent_id}/approve", response_model=APIResponse[AgentAdminResponse])
async def approve_agent(
    agent_id: UUID,
    payload: AgentApproveRequest,
    session: SessionDep,
    admin: AdminDep,
) -> APIResponse[AgentAdminResponse]:
    agent = await AgentService(session).approve_agent(
        agent_id=agent_id,
        admin=admin,
        note=payload.note,
        allow_unpaid_override=payload.allow_unpaid_override,
    )
    return APIResponse(message="Agent approved", data=AgentAdminResponse.model_validate(agent))


@router.patch("/agents/{agent_id}/reject", response_model=APIResponse[AgentAdminResponse])
async def reject_agent(
    agent_id: UUID,
    payload: AgentStatusChangeRequest,
    session: SessionDep,
    admin: AdminDep,
) -> APIResponse[AgentAdminResponse]:
    agent = await AgentService(session).reject_agent(agent_id=agent_id, admin=admin, note=payload.note)
    return APIResponse(message="Agent rejected", data=AgentAdminResponse.model_validate(agent))


@router.patch("/agents/{agent_id}/disable", response_model=APIResponse[AgentAdminResponse])
async def disable_agent(
    agent_id: UUID,
    payload: AgentStatusChangeRequest,
    session: SessionDep,
    admin: AdminDep,
) -> APIResponse[AgentAdminResponse]:
    agent = await AgentService(session).disable_agent(agent_id=agent_id, admin=admin, note=payload.note)
    return APIResponse(message="Agent disabled", data=AgentAdminResponse.model_validate(agent))


@router.patch("/agents/{agent_id}/enable", response_model=APIResponse[AgentAdminResponse])
async def enable_agent(
    agent_id: UUID,
    payload: AgentStatusChangeRequest,
    session: SessionDep,
    admin: AdminDep,
) -> APIResponse[AgentAdminResponse]:
    agent = await AgentService(session).enable_agent(agent_id=agent_id, admin=admin, note=payload.note)
    return APIResponse(message="Agent enabled", data=AgentAdminResponse.model_validate(agent))


@router.get("/properties", response_model=APIResponse[PaginatedResponse[PropertyResponse]])
async def list_admin_properties(
    session: SessionDep,
    _admin: AdminDep,
    q: str | None = Query(default=None, max_length=100),
    country: str | None = Query(default=None, max_length=100),
    state: str | None = Query(default=None, max_length=100),
    local_government: str | None = Query(default=None, max_length=120),
    community: str | None = Query(default=None, max_length=160),
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    category: PropertyCategory | None = Query(default=None),
    listing_type: ListingType | None = Query(default=None),
    property_status: PropertyStatus | None = Query(default=None, alias="status"),
    sort: PropertySort = Query(default=PropertySort.NEWEST),
    agent_id: UUID | None = Query(default=None),
    include_deleted: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> APIResponse[PaginatedResponse[PropertyResponse]]:
    properties, total = await PropertyService(session).list_admin_properties(
        page=page,
        limit=limit,
        q=q,
        country=country,
        state=state,
        local_government=local_government,
        community=community,
        min_price=min_price,
        max_price=max_price,
        category=category,
        listing_type=listing_type,
        status=property_status,
        sort=sort,
        agent_id=agent_id,
        include_deleted=include_deleted,
    )
    return APIResponse(
        message="Admin properties retrieved",
        data=PaginatedResponse(
            items=[PropertyResponse.model_validate(property_obj) for property_obj in properties],
            meta=PaginationMeta(page=page, limit=limit, total=total),
        ),
    )


@router.get("/properties/{property_id}", response_model=APIResponse[PropertyResponse])
async def get_admin_property(property_id: UUID, session: SessionDep, _admin: AdminDep) -> APIResponse[PropertyResponse]:
    property_obj = await PropertyService(session).get_admin_property(property_id)
    return APIResponse(message="Admin property retrieved", data=PropertyResponse.model_validate(property_obj))


@router.patch("/properties/{property_id}/hide", response_model=APIResponse[PropertyResponse])
async def hide_admin_property(
    property_id: UUID,
    payload: AdminPropertyStatusRequest,
    session: SessionDep,
    admin: AdminDep,
) -> APIResponse[PropertyResponse]:
    property_obj = await PropertyService(session).hide_property_for_admin(property_id=property_id, admin=admin, note=payload.note)
    return APIResponse(message="Property hidden", data=PropertyResponse.model_validate(property_obj))


@router.patch("/properties/{property_id}/restore", response_model=APIResponse[PropertyResponse])
async def restore_admin_property(
    property_id: UUID,
    payload: AdminPropertyRestoreRequest,
    session: SessionDep,
    admin: AdminDep,
) -> APIResponse[PropertyResponse]:
    property_obj = await PropertyService(session).restore_property_for_admin(
        property_id=property_id,
        admin=admin,
        status=payload.status,
        is_published=payload.is_published,
        note=payload.note,
    )
    return APIResponse(message="Property restored", data=PropertyResponse.model_validate(property_obj))


@router.delete("/properties/{property_id}", response_model=APIResponse[dict[str, bool]])
async def delete_admin_property(
    property_id: UUID,
    session: SessionDep,
    admin: AdminDep,
    note: str | None = Query(default=None, max_length=1000),
) -> APIResponse[dict[str, bool]]:
    await PropertyService(session).soft_delete_property_for_admin(property_id=property_id, admin=admin, note=note)
    return APIResponse(message="Property deleted by admin", data={"deleted": True})


@router.get("/activity-logs", response_model=APIResponse[PaginatedResponse[AdminActivityLogResponse]])
async def list_activity_logs(
    session: SessionDep,
    _admin: AdminDep,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> APIResponse[PaginatedResponse[AdminActivityLogResponse]]:
    logs, total = await AdminRepository(session).list_activity_logs(page=page, limit=limit)
    items = [AdminActivityLogResponse.model_validate(log) for log in logs]
    return APIResponse(
        message="Admin activity logs retrieved",
        data=PaginatedResponse(items=items, meta=PaginationMeta(page=page, limit=limit, total=total)),
    )

```


## `migrations/versions/0003_add_property_search_indexes.py`

```python
"""add property search indexes

Revision ID: 0003_add_property_search_indexes
Revises: 0002_add_properties_and_media
Create Date: 2026-05-08
"""

from alembic import op

revision = "0003_add_property_search_indexes"
down_revision = "0002_add_properties_and_media"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_properties_search_vector
        ON properties
        USING GIN (
            to_tsvector(
                'simple',
                coalesce(title, '') || ' ' ||
                coalesce(description, '') || ' ' ||
                coalesce(country, '') || ' ' ||
                coalesce(state, '') || ' ' ||
                coalesce(local_government, '') || ' ' ||
                coalesce(community, '')
            )
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_properties_created_at ON properties (created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_properties_listing_type_status ON properties (listing_type, status)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_properties_listing_type_status")
    op.execute("DROP INDEX IF EXISTS ix_properties_created_at")
    op.execute("DROP INDEX IF EXISTS ix_properties_search_vector")

```
