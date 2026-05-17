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
