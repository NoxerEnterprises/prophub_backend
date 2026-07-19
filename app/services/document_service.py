from __future__ import annotations

import re
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AdminAction, DocumentStatus, DocumentType, OperatingMode
from app.core.exceptions import BadRequestError, NotFoundError
from app.core.security import now_utc
from app.models.agent_profile import AgentProfile
from app.models.user import User
from app.models.user_document import UserDocument
from app.repositories.document_repository import DocumentRepository
from app.services.admin_activity_service import AdminActivityService
from app.services.storage_service import SupabaseStorageService


class DocumentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.documents = DocumentRepository(session)
        self.activity = AdminActivityService(session)

    async def upsert_agent_document(self, *, user: User, agent: AgentProfile, document_type: DocumentType, document_number: str, file: UploadFile) -> UserDocument:
        document_number = document_number.strip().upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9\-/]{1,119}", document_number):
            raise BadRequestError(f"{document_type.value} document number must be alphanumeric and may include '-' or '/'")
        extension = Path(file.filename or "").suffix.lower()
        path = f"documents/{user.id}/{document_type.value.lower()}/{uuid.uuid4()}{extension}"
        uploaded = await SupabaseStorageService().upload_document(file=file, path=path)
        existing = await self.documents.get_agent_document(agent_profile_id=agent.id, document_type=document_type.value)
        if existing:
            if existing.storage_path:
                try:
                    await SupabaseStorageService().delete_object(existing.storage_path)
                except Exception:
                    pass
            existing.document_number = document_number
            existing.file_url = uploaded.public_url
            existing.storage_path = uploaded.path
            existing.content_type = uploaded.content_type
            existing.file_size_bytes = uploaded.size_bytes
            existing.status = DocumentStatus.PENDING.value
            existing.rejection_reason = None
            existing.reviewed_at = None
            existing.reviewed_by_id = None
            return existing
        document = UserDocument(user_id=user.id, agent_profile_id=agent.id, document_type=document_type.value, document_number=document_number, file_url=uploaded.public_url, storage_path=uploaded.path, content_type=uploaded.content_type, file_size_bytes=uploaded.size_bytes, status=DocumentStatus.PENDING.value)
        await self.documents.add(document)
        return document

    async def list_my_documents(self, user: User) -> list[UserDocument]:
        return await self.documents.list_for_user(user.id)

    async def list_documents_for_admin(self, *, page: int, limit: int, status: DocumentStatus | None = None, document_type: DocumentType | None = None, user_id: UUID | None = None, agent_profile_id: UUID | None = None) -> tuple[list[UserDocument], int]:
        return await self.documents.list_for_admin(page=page, limit=limit, status=status.value if status else None, document_type=document_type.value if document_type else None, user_id=user_id, agent_profile_id=agent_profile_id)

    async def approve_document(self, *, document_id: UUID, admin: User, note: str | None = None) -> UserDocument:
        document = await self.documents.get_by_id(document_id)
        if not document:
            raise NotFoundError("Document not found")
        document.status = DocumentStatus.APPROVED.value
        document.rejection_reason = None
        document.reviewed_by_id = admin.id
        document.reviewed_at = now_utc()
        if document.document_type == DocumentType.CAC.value and document.agent_profile:
            document.agent_profile.operating_mode = OperatingMode.STANDALONE.value
        await self.activity.log(admin_id=admin.id, action=AdminAction.DOCUMENT_APPROVED.value, target_type="user_document", target_id=document.id, description=note, metadata={"document_type": document.document_type, "user_id": str(document.user_id)})
        await self.session.commit()
        await self.session.refresh(document, attribute_names=["user", "agent_profile"])
        return document

    async def reject_document(self, *, document_id: UUID, admin: User, reason: str) -> UserDocument:
        document = await self.documents.get_by_id(document_id)
        if not document:
            raise NotFoundError("Document not found")
        document.status = DocumentStatus.REJECTED.value
        document.rejection_reason = reason
        document.reviewed_by_id = admin.id
        document.reviewed_at = now_utc()
        if document.document_type == DocumentType.CAC.value and document.agent_profile:
            document.agent_profile.operating_mode = OperatingMode.NOXER_MANAGED.value
        await self.activity.log(admin_id=admin.id, action=AdminAction.DOCUMENT_REJECTED.value, target_type="user_document", target_id=document.id, description=reason, metadata={"document_type": document.document_type, "user_id": str(document.user_id)})
        await self.session.commit()
        await self.session.refresh(document, attribute_names=["user", "agent_profile"])
        return document

    async def has_approved_document(self, *, agent_id: UUID, document_type: DocumentType) -> bool:
        document = await self.documents.get_agent_document(agent_profile_id=agent_id, document_type=document_type.value)
        return bool(document and document.status == DocumentStatus.APPROVED.value)
