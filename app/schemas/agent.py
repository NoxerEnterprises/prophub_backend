from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from app.core.enums import AgentStatus, OperatingMode, SubscriptionStatus, UserType
from app.schemas.common import ORMModel
from app.schemas.document import DocumentResponse
from app.schemas.user import UserPublic


class AgentProfileBase(ORMModel):
    user_type: UserType
    business_name: str = Field(min_length=2, max_length=160)
    business_phone: str | None = Field(default=None, max_length=32)
    business_email: EmailStr | None = None
    license_number: str | None = Field(default=None, max_length=100)
    address: str | None = None
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    country: str = Field(default="Nigeria", max_length=100)


class AgentProfileCreate(AgentProfileBase):
    pass


class AgentProfileUpdate(ORMModel):
    business_name: str | None = Field(default=None, min_length=2, max_length=160)
    business_phone: str | None = Field(default=None, max_length=32)
    business_email: EmailStr | None = None
    license_number: str | None = Field(default=None, max_length=100)
    address: str | None = None
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)


class AgentProfileResponse(ORMModel):
    id: UUID
    user_id: UUID
    user_type: UserType | str
    operating_mode: OperatingMode | str
    business_name: str
    business_phone: str | None = None
    business_email: str | None = None
    license_number: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str
    status: AgentStatus | str
    previous_status: AgentStatus | str | None = None
    status_note: str | None = None
    subscription_status: SubscriptionStatus | str
    subscription_started_at: datetime | None = None
    subscription_expires_at: datetime | None = None
    last_subscription_transaction_id: UUID | None = None
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    disabled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AgentProfileDetailResponse(AgentProfileResponse):
    documents: list[DocumentResponse] = []


class AgentAdminResponse(AgentProfileResponse):
    user: UserPublic
    documents: list[DocumentResponse] = []


class AgentStatusChangeRequest(ORMModel):
    note: str | None = Field(default=None, max_length=1000)


class AgentApproveRequest(AgentStatusChangeRequest):
    allow_override: bool = False
    allow_unpaid_override: bool = False  # legacy alias accepted by existing mobile/admin tools
