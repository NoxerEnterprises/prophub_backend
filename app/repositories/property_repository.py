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
