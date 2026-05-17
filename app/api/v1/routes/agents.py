from fastapi import APIRouter, status

from app.api.dependencies import CurrentUserDep, SessionDep
from app.schemas.agent import AgentProfileCreate, AgentProfileResponse, AgentProfileUpdate
from app.schemas.common import APIResponse
from app.services.agent_service import AgentService

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.post("/me", status_code=status.HTTP_201_CREATED, response_model=APIResponse[AgentProfileResponse])
async def create_my_agent_profile(
    payload: AgentProfileCreate,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> APIResponse[AgentProfileResponse]:
    agent = await AgentService(session).create_my_agent_profile(current_user, payload)
    return APIResponse(message="Agent profile created", data=AgentProfileResponse.model_validate(agent))


@router.get("/me", response_model=APIResponse[AgentProfileResponse])
async def get_my_agent_profile(current_user: CurrentUserDep, session: SessionDep) -> APIResponse[AgentProfileResponse]:
    agent = await AgentService(session).get_my_agent_profile(current_user)
    return APIResponse(message="Agent profile", data=AgentProfileResponse.model_validate(agent))


@router.patch("/me", response_model=APIResponse[AgentProfileResponse])
async def update_my_agent_profile(
    payload: AgentProfileUpdate,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> APIResponse[AgentProfileResponse]:
    agent = await AgentService(session).update_my_agent_profile(current_user, payload)
    return APIResponse(message="Agent profile updated", data=AgentProfileResponse.model_validate(agent))
