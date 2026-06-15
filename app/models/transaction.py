from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import TransactionProvider, TransactionStatus, TransactionType
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.agent_profile import AgentProfile
    from app.models.user import User


class Transaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transactions"
    __table_args__ = (UniqueConstraint("reference", name="uq_transactions_reference"),)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_profiles.id", ondelete="CASCADE"), index=True, nullable=False)

    provider: Mapped[str] = mapped_column(String(40), default=TransactionProvider.PAYSTACK.value, index=True, nullable=False)
    payment_type: Mapped[str] = mapped_column(String(60), default=TransactionType.AGENT_VERIFICATION.value, index=True, nullable=False)
    reference: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="NGN", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default=TransactionStatus.PENDING.value, index=True, nullable=False)

    authorization_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_response: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    user: Mapped[User] = relationship("User", lazy="selectin")
    agent: Mapped[AgentProfile] = relationship("AgentProfile", lazy="selectin")
