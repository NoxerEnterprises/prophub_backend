from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import SessionDep, require_approved_agent
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.schemas.property import PropertyResponse
from app.services.agent_service import AgentService
from app.services.property_service import PropertyService

router = APIRouter(prefix="/agents/me/properties", tags=["Agent Properties"])
ApprovedAgentDep = Annotated[User, Depends(require_approved_agent)]


@router.get("", response_model=APIResponse[PaginatedResponse[PropertyResponse]])
async def list_my_properties(
    current_user: ApprovedAgentDep,
    session: SessionDep,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> APIResponse[PaginatedResponse[PropertyResponse]]:
    agent = await AgentService(session).get_my_agent_profile(current_user)
    properties, total = await PropertyService(session).list_my_properties(agent=agent, page=page, limit=limit)
    return APIResponse(
        message="Agent properties retrieved",
        data=PaginatedResponse(
            items=[PropertyResponse.model_validate(property_obj) for property_obj in properties],
            meta=PaginationMeta(page=page, limit=limit, total=total),
        ),
    )
