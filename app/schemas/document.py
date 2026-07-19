from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.core.enums import DocumentStatus, DocumentType
from app.schemas.common import ORMModel
from app.schemas.user import UserPublic


class DocumentResponse(ORMModel):
    id: UUID
    user_id: UUID
    agent_profile_id: UUID | None = None
    document_type: DocumentType | str
    document_number: str
    file_url: str
    storage_path: str
    content_type: str
    file_size_bytes: int
    status: DocumentStatus | str
    rejection_reason: str | None = None
    reviewed_by_id: UUID | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AdminDocumentResponse(DocumentResponse):
    user: UserPublic | None = None


class DocumentReviewRequest(ORMModel):
    note: str | None = Field(default=None, max_length=1000)


class DocumentRejectRequest(ORMModel):
    reason: str = Field(min_length=2, max_length=1000)
