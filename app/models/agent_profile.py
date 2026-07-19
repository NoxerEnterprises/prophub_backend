from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import AgentStatus, OperatingMode, SubscriptionStatus, UserType
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.property import Property
    from app.models.transaction import Transaction
    from app.models.user import User
    from app.models.user_document import UserDocument


class AgentProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    user_type: Mapped[str] = mapped_column(String(64), default=UserType.BUSINESS_AGENT.value, index=True, nullable=False)
    operating_mode: Mapped[str] = mapped_column(String(32), default=OperatingMode.NOXER_MANAGED.value, index=True, nullable=False)

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

    subscription_status: Mapped[str] = mapped_column(String(32), default=SubscriptionStatus.INACTIVE.value, index=True, nullable=False)
    subscription_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    subscription_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    last_subscription_transaction_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=True)

    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disabled_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="agent_profile", lazy="selectin", foreign_keys=[user_id])
    documents: Mapped[list[UserDocument]] = relationship("UserDocument", back_populates="agent_profile", lazy="selectin", cascade="all, delete-orphan")
    properties: Mapped[list[Property]] = relationship("Property", back_populates="agent", lazy="selectin", cascade="all, delete-orphan")
    last_subscription_transaction: Mapped[Transaction | None] = relationship("Transaction", lazy="selectin", foreign_keys=[last_subscription_transaction_id])
