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
