from __future__ import annotations

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import SessionDep, require_admin
from app.core.enums import AgentStatus, ListingType, PropertyCategory, PropertySort, PropertyStatus
from app.models.user import User
from app.repositories.admin_repository import AdminRepository
from app.schemas.admin import AdminActivityLogResponse
from app.schemas.agent import AgentAdminResponse, AgentApproveRequest, AgentStatusChangeRequest
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.schemas.property import AdminPropertyRestoreRequest, AdminPropertyStatusRequest, PropertyResponse
from app.services.agent_service import AgentService
from app.services.property_service import PropertyService

router = APIRouter(prefix="/admin", tags=["Admin"])

AdminDep = Annotated[User, Depends(require_admin)]


@router.get("/agents", response_model=APIResponse[PaginatedResponse[AgentAdminResponse]])
async def list_agents(
    session: SessionDep,
    _admin: AdminDep,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    status: AgentStatus | None = Query(default=None),
    q: str | None = Query(default=None, max_length=100),
) -> APIResponse[PaginatedResponse[AgentAdminResponse]]:
    agents, total = await AgentService(session).list_agents(page=page, limit=limit, status=status, q=q)
    items = [AgentAdminResponse.model_validate(agent) for agent in agents]
    return APIResponse(
        message="Agents retrieved",
        data=PaginatedResponse(items=items, meta=PaginationMeta(page=page, limit=limit, total=total)),
    )


@router.get("/agents/{agent_id}", response_model=APIResponse[AgentAdminResponse])
async def get_agent(agent_id: UUID, session: SessionDep, _admin: AdminDep) -> APIResponse[AgentAdminResponse]:
    agent = await AgentService(session).get_agent_for_admin(agent_id)
    return APIResponse(message="Agent retrieved", data=AgentAdminResponse.model_validate(agent))


@router.patch("/agents/{agent_id}/approve", response_model=APIResponse[AgentAdminResponse])
async def approve_agent(
    agent_id: UUID,
    payload: AgentApproveRequest,
    session: SessionDep,
    admin: AdminDep,
) -> APIResponse[AgentAdminResponse]:
    agent = await AgentService(session).approve_agent(
        agent_id=agent_id,
        admin=admin,
        note=payload.note,
        allow_unpaid_override=payload.allow_unpaid_override,
    )
    return APIResponse(message="Agent approved", data=AgentAdminResponse.model_validate(agent))


@router.patch("/agents/{agent_id}/reject", response_model=APIResponse[AgentAdminResponse])
async def reject_agent(
    agent_id: UUID,
    payload: AgentStatusChangeRequest,
    session: SessionDep,
    admin: AdminDep,
) -> APIResponse[AgentAdminResponse]:
    agent = await AgentService(session).reject_agent(agent_id=agent_id, admin=admin, note=payload.note)
    return APIResponse(message="Agent rejected", data=AgentAdminResponse.model_validate(agent))


@router.patch("/agents/{agent_id}/disable", response_model=APIResponse[AgentAdminResponse])
async def disable_agent(
    agent_id: UUID,
    payload: AgentStatusChangeRequest,
    session: SessionDep,
    admin: AdminDep,
) -> APIResponse[AgentAdminResponse]:
    agent = await AgentService(session).disable_agent(agent_id=agent_id, admin=admin, note=payload.note)
    return APIResponse(message="Agent disabled", data=AgentAdminResponse.model_validate(agent))


@router.patch("/agents/{agent_id}/enable", response_model=APIResponse[AgentAdminResponse])
async def enable_agent(
    agent_id: UUID,
    payload: AgentStatusChangeRequest,
    session: SessionDep,
    admin: AdminDep,
) -> APIResponse[AgentAdminResponse]:
    agent = await AgentService(session).enable_agent(agent_id=agent_id, admin=admin, note=payload.note)
    return APIResponse(message="Agent enabled", data=AgentAdminResponse.model_validate(agent))


@router.get("/properties", response_model=APIResponse[PaginatedResponse[PropertyResponse]])
async def list_admin_properties(
    session: SessionDep,
    _admin: AdminDep,
    q: str | None = Query(default=None, max_length=100),
    country: str | None = Query(default=None, max_length=100),
    state: str | None = Query(default=None, max_length=100),
    local_government: str | None = Query(default=None, max_length=120),
    community: str | None = Query(default=None, max_length=160),
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    category: PropertyCategory | None = Query(default=None),
    listing_type: ListingType | None = Query(default=None),
    property_status: PropertyStatus | None = Query(default=None, alias="status"),
    sort: PropertySort = Query(default=PropertySort.NEWEST),
    agent_id: UUID | None = Query(default=None),
    include_deleted: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> APIResponse[PaginatedResponse[PropertyResponse]]:
    properties, total = await PropertyService(session).list_admin_properties(
        page=page,
        limit=limit,
        q=q,
        country=country,
        state=state,
        local_government=local_government,
        community=community,
        min_price=min_price,
        max_price=max_price,
        category=category,
        listing_type=listing_type,
        status=property_status,
        sort=sort,
        agent_id=agent_id,
        include_deleted=include_deleted,
    )
    return APIResponse(
        message="Admin properties retrieved",
        data=PaginatedResponse(
            items=[PropertyResponse.model_validate(property_obj) for property_obj in properties],
            meta=PaginationMeta(page=page, limit=limit, total=total),
        ),
    )


@router.get("/properties/{property_id}", response_model=APIResponse[PropertyResponse])
async def get_admin_property(property_id: UUID, session: SessionDep, _admin: AdminDep) -> APIResponse[PropertyResponse]:
    property_obj = await PropertyService(session).get_admin_property(property_id)
    return APIResponse(message="Admin property retrieved", data=PropertyResponse.model_validate(property_obj))


@router.patch("/properties/{property_id}/hide", response_model=APIResponse[PropertyResponse])
async def hide_admin_property(
    property_id: UUID,
    payload: AdminPropertyStatusRequest,
    session: SessionDep,
    admin: AdminDep,
) -> APIResponse[PropertyResponse]:
    property_obj = await PropertyService(session).hide_property_for_admin(property_id=property_id, admin=admin, note=payload.note)
    return APIResponse(message="Property hidden", data=PropertyResponse.model_validate(property_obj))


@router.patch("/properties/{property_id}/restore", response_model=APIResponse[PropertyResponse])
async def restore_admin_property(
    property_id: UUID,
    payload: AdminPropertyRestoreRequest,
    session: SessionDep,
    admin: AdminDep,
) -> APIResponse[PropertyResponse]:
    property_obj = await PropertyService(session).restore_property_for_admin(
        property_id=property_id,
        admin=admin,
        status=payload.status,
        is_published=payload.is_published,
        note=payload.note,
    )
    return APIResponse(message="Property restored", data=PropertyResponse.model_validate(property_obj))


@router.delete("/properties/{property_id}", response_model=APIResponse[dict[str, bool]])
async def delete_admin_property(
    property_id: UUID,
    session: SessionDep,
    admin: AdminDep,
    note: str | None = Query(default=None, max_length=1000),
) -> APIResponse[dict[str, bool]]:
    await PropertyService(session).soft_delete_property_for_admin(property_id=property_id, admin=admin, note=note)
    return APIResponse(message="Property deleted by admin", data={"deleted": True})


@router.get("/activity-logs", response_model=APIResponse[PaginatedResponse[AdminActivityLogResponse]])
async def list_activity_logs(
    session: SessionDep,
    _admin: AdminDep,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> APIResponse[PaginatedResponse[AdminActivityLogResponse]]:
    logs, total = await AdminRepository(session).list_activity_logs(page=page, limit=limit)
    items = [AdminActivityLogResponse.model_validate(log) for log in logs]
    return APIResponse(
        message="Admin activity logs retrieved",
        data=PaginatedResponse(items=items, meta=PaginationMeta(page=page, limit=limit, total=total)),
    )
