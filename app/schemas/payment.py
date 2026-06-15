from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.core.enums import TransactionProvider, TransactionStatus, TransactionType


class PaymentInitializeRequest(BaseModel):
    callback_url: HttpUrl | None = None


class PaymentInitializeResponse(BaseModel):
    reference: str
    amount: Decimal
    currency: str
    authorization_url: str
    access_code: str | None = None
    public_key: str | None = None


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    agent_id: UUID
    provider: TransactionProvider | str
    payment_type: TransactionType | str
    reference: str
    amount: Decimal
    currency: str
    status: TransactionStatus | str
    authorization_url: str | None = None
    access_code: str | None = None
    paid_at: datetime | None = None
    verified_at: datetime | None = None
    failure_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class PaymentVerifyResponse(BaseModel):
    transaction: TransactionResponse
    agent_status: str


class AdminTransactionFilter(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
