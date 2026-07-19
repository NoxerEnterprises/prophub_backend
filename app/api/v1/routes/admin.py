from __future__ import annotations

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import SessionDep, require_admin, require_super_admin
from app.core.enums import AgentStatus, DocumentStatus, DocumentType, ListingType, OperatingMode, PropertyCategory, PropertySort, PropertyStatus, SubscriptionStatus, TransactionStatus, UserType
from app.models.user import User
from app.repositories.admin_repository import AdminRepository
from app.schemas.admin import AdminActivityLogResponse, AdminCreateRequest, AdminProfileResponse, AdminUpdateRequest
from app.schemas.agent import AgentAdminResponse, AgentApproveRequest, AgentStatusChangeRequest
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.schemas.document import AdminDocumentResponse, DocumentRejectRequest, DocumentReviewRequest
from app.schemas.payment import TransactionResponse
from app.schemas.property import AdminPropertyRestoreRequest, AdminPropertyStatusRequest, PropertyResponse
from app.services.admin_service import AdminService
from app.services.agent_service import AgentService
from app.services.document_service import DocumentService
from app.services.payment_service import PaymentService
from app.services.property_service import PropertyService

router = APIRouter(prefix="/admin", tags=["Admin"])
AdminDep = Annotated[User, Depends(require_admin)]
SuperAdminDep = Annotated[User, Depends(require_super_admin)]


@router.post("/admins", response_model=APIResponse[AdminProfileResponse])
async def create_admin(payload: AdminCreateRequest, session: SessionDep, super_admin: SuperAdminDep) -> APIResponse[AdminProfileResponse]:
    profile = await AdminService(session).create_admin(actor=super_admin, payload=payload)
    return APIResponse(message="Admin created", data=AdminProfileResponse.model_validate(profile))


@router.get("/admins", response_model=APIResponse[PaginatedResponse[AdminProfileResponse]])
async def list_admins(session: SessionDep, _super_admin: SuperAdminDep, page: int = Query(default=1, ge=1), limit: int = Query(default=20, ge=1, le=100)) -> APIResponse[PaginatedResponse[AdminProfileResponse]]:
    admins, total = await AdminService(session).list_admins(page=page, limit=limit)
    return APIResponse(message="Admins retrieved", data=PaginatedResponse(items=[AdminProfileResponse.model_validate(admin) for admin in admins], meta=PaginationMeta(page=page, limit=limit, total=total)))


@router.get("/admins/{admin_id}", response_model=APIResponse[AdminProfileResponse])
async def get_admin(admin_id: UUID, session: SessionDep, _super_admin: SuperAdminDep) -> APIResponse[AdminProfileResponse]:
    profile = await AdminService(session).get_admin(admin_id)
    return APIResponse(message="Admin retrieved", data=AdminProfileResponse.model_validate(profile))


@router.patch("/admins/{admin_id}", response_model=APIResponse[AdminProfileResponse])
async def update_admin(admin_id: UUID, payload: AdminUpdateRequest, session: SessionDep, super_admin: SuperAdminDep) -> APIResponse[AdminProfileResponse]:
    profile = await AdminService(session).update_admin(actor=super_admin, admin_id=admin_id, payload=payload)
    return APIResponse(message="Admin updated", data=AdminProfileResponse.model_validate(profile))


@router.patch("/admins/{admin_id}/disable", response_model=APIResponse[AdminProfileResponse])
async def disable_admin(admin_id: UUID, session: SessionDep, super_admin: SuperAdminDep) -> APIResponse[AdminProfileResponse]:
    profile = await AdminService(session).set_admin_active(actor=super_admin, admin_id=admin_id, is_active=False)
    return APIResponse(message="Admin disabled", data=AdminProfileResponse.model_validate(profile))


@router.patch("/admins/{admin_id}/enable", response_model=APIResponse[AdminProfileResponse])
async def enable_admin(admin_id: UUID, session: SessionDep, super_admin: SuperAdminDep) -> APIResponse[AdminProfileResponse]:
    profile = await AdminService(session).set_admin_active(actor=super_admin, admin_id=admin_id, is_active=True)
    return APIResponse(message="Admin enabled", data=AdminProfileResponse.model_validate(profile))


@router.get("/agents", response_model=APIResponse[PaginatedResponse[AgentAdminResponse]])
async def list_agents(session: SessionDep, _admin: AdminDep, page: int = Query(default=1, ge=1), limit: int = Query(default=20, ge=1, le=100), status: AgentStatus | None = Query(default=None), user_type: UserType | None = Query(default=None), operating_mode: OperatingMode | None = Query(default=None), subscription_status: SubscriptionStatus | None = Query(default=None), q: str | None = Query(default=None, max_length=100)) -> APIResponse[PaginatedResponse[AgentAdminResponse]]:
    agents, total = await AgentService(session).list_agents(page=page, limit=limit, status=status, q=q, user_type=user_type, operating_mode=operating_mode, subscription_status=subscription_status)
    return APIResponse(message="Agents retrieved", data=PaginatedResponse(items=[AgentAdminResponse.model_validate(agent) for agent in agents], meta=PaginationMeta(page=page, limit=limit, total=total)))


@router.get("/agents/{agent_id}", response_model=APIResponse[AgentAdminResponse])
async def get_agent(agent_id: UUID, session: SessionDep, _admin: AdminDep) -> APIResponse[AgentAdminResponse]:
    agent = await AgentService(session).get_agent_for_admin(agent_id)
    return APIResponse(message="Agent retrieved", data=AgentAdminResponse.model_validate(agent))


@router.patch("/agents/{agent_id}/approve", response_model=APIResponse[AgentAdminResponse])
async def approve_agent(agent_id: UUID, payload: AgentApproveRequest, session: SessionDep, admin: AdminDep) -> APIResponse[AgentAdminResponse]:
    agent = await AgentService(session).approve_agent(agent_id=agent_id, admin=admin, note=payload.note, allow_override=payload.allow_override, allow_unpaid_override=payload.allow_unpaid_override)
    return APIResponse(message="Agent approved", data=AgentAdminResponse.model_validate(agent))


@router.patch("/agents/{agent_id}/reject", response_model=APIResponse[AgentAdminResponse])
async def reject_agent(agent_id: UUID, payload: AgentStatusChangeRequest, session: SessionDep, admin: AdminDep) -> APIResponse[AgentAdminResponse]:
    agent = await AgentService(session).reject_agent(agent_id=agent_id, admin=admin, note=payload.note)
    return APIResponse(message="Agent rejected", data=AgentAdminResponse.model_validate(agent))


@router.patch("/agents/{agent_id}/disable", response_model=APIResponse[AgentAdminResponse])
async def disable_agent(agent_id: UUID, payload: AgentStatusChangeRequest, session: SessionDep, admin: AdminDep) -> APIResponse[AgentAdminResponse]:
    agent = await AgentService(session).disable_agent(agent_id=agent_id, admin=admin, note=payload.note)
    return APIResponse(message="Agent disabled", data=AgentAdminResponse.model_validate(agent))


@router.patch("/agents/{agent_id}/enable", response_model=APIResponse[AgentAdminResponse])
async def enable_agent(agent_id: UUID, payload: AgentStatusChangeRequest, session: SessionDep, admin: AdminDep) -> APIResponse[AgentAdminResponse]:
    agent = await AgentService(session).enable_agent(agent_id=agent_id, admin=admin, note=payload.note)
    return APIResponse(message="Agent enabled", data=AgentAdminResponse.model_validate(agent))


@router.get("/documents", response_model=APIResponse[PaginatedResponse[AdminDocumentResponse]])
async def list_documents(session: SessionDep, _admin: AdminDep, status: DocumentStatus | None = Query(default=None), document_type: DocumentType | None = Query(default=None), user_id: UUID | None = Query(default=None), agent_profile_id: UUID | None = Query(default=None), page: int = Query(default=1, ge=1), limit: int = Query(default=20, ge=1, le=100)) -> APIResponse[PaginatedResponse[AdminDocumentResponse]]:
    docs, total = await DocumentService(session).list_documents_for_admin(page=page, limit=limit, status=status, document_type=document_type, user_id=user_id, agent_profile_id=agent_profile_id)
    return APIResponse(message="Documents retrieved", data=PaginatedResponse(items=[AdminDocumentResponse.model_validate(doc) for doc in docs], meta=PaginationMeta(page=page, limit=limit, total=total)))


@router.patch("/documents/{document_id}/approve", response_model=APIResponse[AdminDocumentResponse])
async def approve_document(document_id: UUID, payload: DocumentReviewRequest, session: SessionDep, admin: AdminDep) -> APIResponse[AdminDocumentResponse]:
    doc = await DocumentService(session).approve_document(document_id=document_id, admin=admin, note=payload.note)
    return APIResponse(message="Document approved", data=AdminDocumentResponse.model_validate(doc))


@router.patch("/documents/{document_id}/reject", response_model=APIResponse[AdminDocumentResponse])
async def reject_document(document_id: UUID, payload: DocumentRejectRequest, session: SessionDep, admin: AdminDep) -> APIResponse[AdminDocumentResponse]:
    doc = await DocumentService(session).reject_document(document_id=document_id, admin=admin, reason=payload.reason)
    return APIResponse(message="Document rejected", data=AdminDocumentResponse.model_validate(doc))


@router.get("/properties", response_model=APIResponse[PaginatedResponse[PropertyResponse]])
async def list_admin_properties(session: SessionDep, _admin: AdminDep, q: str | None = Query(default=None, max_length=100), country: str | None = Query(default=None, max_length=100), state: str | None = Query(default=None, max_length=100), local_government: str | None = Query(default=None, max_length=120), community: str | None = Query(default=None, max_length=160), min_price: Decimal | None = Query(default=None, ge=0), max_price: Decimal | None = Query(default=None, ge=0), category: PropertyCategory | None = Query(default=None), listing_type: ListingType | None = Query(default=None), property_status: PropertyStatus | None = Query(default=None, alias="status"), sort: PropertySort = Query(default=PropertySort.NEWEST), agent_id: UUID | None = Query(default=None), include_deleted: bool = Query(default=False), page: int = Query(default=1, ge=1), limit: int = Query(default=20, ge=1, le=100)) -> APIResponse[PaginatedResponse[PropertyResponse]]:
    properties, total = await PropertyService(session).list_admin_properties(page=page, limit=limit, q=q, country=country, state=state, local_government=local_government, community=community, min_price=min_price, max_price=max_price, category=category, listing_type=listing_type, status=property_status, sort=sort, agent_id=agent_id, include_deleted=include_deleted)
    return APIResponse(message="Admin properties retrieved", data=PaginatedResponse(items=[PropertyResponse.model_validate(p) for p in properties], meta=PaginationMeta(page=page, limit=limit, total=total)))


@router.get("/properties/{property_id}", response_model=APIResponse[PropertyResponse])
async def get_admin_property(property_id: UUID, session: SessionDep, _admin: AdminDep) -> APIResponse[PropertyResponse]:
    property_obj = await PropertyService(session).get_admin_property(property_id)
    return APIResponse(message="Admin property retrieved", data=PropertyResponse.model_validate(property_obj))


@router.patch("/properties/{property_id}/hide", response_model=APIResponse[PropertyResponse])
async def hide_admin_property(property_id: UUID, payload: AdminPropertyStatusRequest, session: SessionDep, admin: AdminDep) -> APIResponse[PropertyResponse]:
    property_obj = await PropertyService(session).hide_property_for_admin(property_id=property_id, admin=admin, note=payload.note)
    return APIResponse(message="Property hidden", data=PropertyResponse.model_validate(property_obj))


@router.patch("/properties/{property_id}/restore", response_model=APIResponse[PropertyResponse])
async def restore_admin_property(property_id: UUID, payload: AdminPropertyRestoreRequest, session: SessionDep, admin: AdminDep) -> APIResponse[PropertyResponse]:
    property_obj = await PropertyService(session).restore_property_for_admin(property_id=property_id, admin=admin, status=payload.status, is_published=payload.is_published, note=payload.note)
    return APIResponse(message="Property restored", data=PropertyResponse.model_validate(property_obj))


@router.delete("/properties/{property_id}", response_model=APIResponse[dict[str, bool]])
async def delete_admin_property(property_id: UUID, session: SessionDep, admin: AdminDep, note: str | None = Query(default=None, max_length=1000)) -> APIResponse[dict[str, bool]]:
    await PropertyService(session).soft_delete_property_for_admin(property_id=property_id, admin=admin, note=note)
    return APIResponse(message="Property deleted by admin", data={"deleted": True})


@router.get("/transactions", response_model=APIResponse[PaginatedResponse[TransactionResponse]])
async def list_admin_transactions(session: SessionDep, _admin: AdminDep, status: TransactionStatus | None = Query(default=None), page: int = Query(default=1, ge=1), limit: int = Query(default=20, ge=1, le=100)) -> APIResponse[PaginatedResponse[TransactionResponse]]:
    transactions, total = await PaymentService(session).list_admin_transactions(page=page, limit=limit, status=status)
    return APIResponse(message="Admin transactions retrieved", data=PaginatedResponse(items=[TransactionResponse.model_validate(t) for t in transactions], meta=PaginationMeta(page=page, limit=limit, total=total)))


@router.get("/activity-logs", response_model=APIResponse[PaginatedResponse[AdminActivityLogResponse]])
async def list_activity_logs(session: SessionDep, _admin: AdminDep, page: int = Query(default=1, ge=1), limit: int = Query(default=20, ge=1, le=100)) -> APIResponse[PaginatedResponse[AdminActivityLogResponse]]:
    logs, total = await AdminRepository(session).list_activity_logs(page=page, limit=limit)
    return APIResponse(message="Admin activity logs retrieved", data=PaginatedResponse(items=[AdminActivityLogResponse.model_validate(log) for log in logs], meta=PaginationMeta(page=page, limit=limit, total=total)))
