from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth import require_admin
from app.db.session import get_db
from app.models.agent_profile import AgentStatus
from app.models.user import User
from app.schemas.agent import (
    AgentApproveRequest,
    AgentDisableRequest,
    AgentEnableRequest,
    AgentListItem,
    AgentListResponse,
    AgentProfilePublic,
    AgentRejectRequest,
)
from app.schemas.response import success_response
from app.services.agent_service import AdminAgentService

router = APIRouter(prefix="/admin/agents", tags=["Admin - Agents"])


@router.get("")
def list_agents(
    status: AgentStatus | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, min_length=2, max_length=255),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = AdminAgentService(db)
    items, total = service.list_agents(
        admin_user=current_user,
        agent_status=status,
        page=page,
        limit=limit,
        search=search,
    )
    data = AgentListResponse(
        items=[AgentListItem.model_validate(item) for item in items],
        page=page,
        limit=limit,
        total=total,
    )
    return success_response(message="Agents retrieved.", data=data.model_dump(mode="json"))


@router.get("/{agent_id}")
def get_agent(
    agent_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    agent = AdminAgentService(db).get_agent(admin_user=current_user, agent_id=agent_id)
    data = AgentProfilePublic.model_validate(agent).model_dump(mode="json")
    return success_response(message="Agent retrieved.", data=data)


@router.patch("/{agent_id}/approve")
def approve_agent(
    agent_id: UUID,
    payload: AgentApproveRequest | None = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    payload = payload or AgentApproveRequest()
    agent = AdminAgentService(db).approve_agent(
        admin_user=current_user,
        agent_id=agent_id,
        allow_unpaid_override=payload.allow_unpaid_override,
        note=payload.note,
    )
    data = AgentProfilePublic.model_validate(agent).model_dump(mode="json")
    return success_response(message="Agent approved.", data=data)


@router.patch("/{agent_id}/reject")
def reject_agent(
    agent_id: UUID,
    payload: AgentRejectRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    agent = AdminAgentService(db).reject_agent(
        admin_user=current_user,
        agent_id=agent_id,
        reason=payload.reason,
    )
    data = AgentProfilePublic.model_validate(agent).model_dump(mode="json")
    return success_response(message="Agent rejected.", data=data)


@router.patch("/{agent_id}/disable")
def disable_agent(
    agent_id: UUID,
    payload: AgentDisableRequest | None = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    payload = payload or AgentDisableRequest()
    agent = AdminAgentService(db).disable_agent(
        admin_user=current_user,
        agent_id=agent_id,
        reason=payload.reason,
    )
    data = AgentProfilePublic.model_validate(agent).model_dump(mode="json")
    return success_response(message="Agent disabled.", data=data)


@router.patch("/{agent_id}/enable")
def enable_agent(
    agent_id: UUID,
    payload: AgentEnableRequest | None = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    payload = payload or AgentEnableRequest()
    agent = AdminAgentService(db).enable_agent(
        admin_user=current_user,
        agent_id=agent_id,
        note=payload.note,
    )
    data = AgentProfilePublic.model_validate(agent).model_dump(mode="json")
    return success_response(message="Agent enabled.", data=data)
