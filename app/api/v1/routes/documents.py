from __future__ import annotations

from uuid import UUID
from fastapi import APIRouter, File, Form, Query, UploadFile

from app.api.dependencies import CurrentUserDep, SessionDep, require_admin
from app.core.enums import DocumentStatus, DocumentType
from app.models.user import User
from typing import Annotated
from fastapi import Depends
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.schemas.document import AdminDocumentResponse, DocumentRejectRequest, DocumentResponse, DocumentReviewRequest
from app.services.agent_service import AgentService
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])
AdminDep = Annotated[User, Depends(require_admin)]


@router.get("/me", response_model=APIResponse[list[DocumentResponse]])
async def list_my_documents(current_user: CurrentUserDep, session: SessionDep) -> APIResponse[list[DocumentResponse]]:
    documents = await DocumentService(session).list_my_documents(current_user)
    return APIResponse(message="Documents retrieved", data=[DocumentResponse.model_validate(doc) for doc in documents])


@router.post("/me", response_model=APIResponse[DocumentResponse])
async def upload_my_document(current_user: CurrentUserDep, session: SessionDep, document_type: DocumentType = Form(...), document_number: str = Form(..., min_length=2, max_length=120), file: UploadFile = File(...)) -> APIResponse[DocumentResponse]:
    agent = await AgentService(session).get_my_agent_profile(current_user)
    document = await DocumentService(session).upsert_agent_document(user=current_user, agent=agent, document_type=document_type, document_number=document_number, file=file)
    await session.commit(); await session.refresh(document)
    return APIResponse(message="Document uploaded", data=DocumentResponse.model_validate(document))


@router.get("/admin", response_model=APIResponse[PaginatedResponse[AdminDocumentResponse]])
async def admin_list_documents(session: SessionDep, _admin: AdminDep, status: DocumentStatus | None = Query(default=None), document_type: DocumentType | None = Query(default=None), user_id: UUID | None = None, agent_profile_id: UUID | None = None, page: int = Query(default=1, ge=1), limit: int = Query(default=20, ge=1, le=100)) -> APIResponse[PaginatedResponse[AdminDocumentResponse]]:
    documents, total = await DocumentService(session).list_documents_for_admin(page=page, limit=limit, status=status, document_type=document_type, user_id=user_id, agent_profile_id=agent_profile_id)
    return APIResponse(message="Documents retrieved", data=PaginatedResponse(items=[AdminDocumentResponse.model_validate(doc) for doc in documents], meta=PaginationMeta(page=page, limit=limit, total=total)))


@router.patch("/admin/{document_id}/approve", response_model=APIResponse[AdminDocumentResponse])
async def admin_approve_document(document_id: UUID, payload: DocumentReviewRequest, session: SessionDep, admin: AdminDep) -> APIResponse[AdminDocumentResponse]:
    document = await DocumentService(session).approve_document(document_id=document_id, admin=admin, note=payload.note)
    return APIResponse(message="Document approved", data=AdminDocumentResponse.model_validate(document))


@router.patch("/admin/{document_id}/reject", response_model=APIResponse[AdminDocumentResponse])
async def admin_reject_document(document_id: UUID, payload: DocumentRejectRequest, session: SessionDep, admin: AdminDep) -> APIResponse[AdminDocumentResponse]:
    document = await DocumentService(session).reject_document(document_id=document_id, admin=admin, reason=payload.reason)
    return APIResponse(message="Document rejected", data=AdminDocumentResponse.model_validate(document))
