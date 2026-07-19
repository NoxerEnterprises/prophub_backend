from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import UserRole, UserType
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.admin_profile import AdminProfile
    from app.models.agent_profile import AgentProfile
    from app.models.email_verification_token import EmailVerificationToken
    from app.models.password_reset_token import PasswordResetToken
    from app.models.refresh_token import RefreshToken
    from app.models.user_document import UserDocument


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("phone", name="uq_users_phone"),
    )

    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default=UserRole.USER.value, index=True, nullable=False)
    user_type: Mapped[str] = mapped_column(String(64), default=UserType.CUSTOMER.value, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    agent_profile: Mapped[AgentProfile | None] = relationship(
        "AgentProfile",
        back_populates="user",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan",
        foreign_keys="AgentProfile.user_id",
    )
    admin_profile: Mapped[AdminProfile | None] = relationship(
        "AdminProfile",
        back_populates="user",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan",
        foreign_keys="AdminProfile.user_id",
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship("RefreshToken", back_populates="user", lazy="selectin", cascade="all, delete-orphan")
    password_reset_tokens: Mapped[list[PasswordResetToken]] = relationship("PasswordResetToken", back_populates="user", lazy="selectin", cascade="all, delete-orphan")
    email_verification_tokens: Mapped[list[EmailVerificationToken]] = relationship("EmailVerificationToken", back_populates="user", lazy="selectin", cascade="all, delete-orphan")
    documents: Mapped[list[UserDocument]] = relationship("UserDocument", back_populates="user", lazy="selectin", cascade="all, delete-orphan", foreign_keys="UserDocument.user_id")
