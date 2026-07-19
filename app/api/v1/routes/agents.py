from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status

from app.api.dependencies import CurrentUserDep, SessionDep
from app.core.enums import UserType
from app.schemas.agent import AgentProfileDetailResponse, AgentProfileResponse, AgentProfileUpdate
from app.schemas.common import APIResponse
from app.services.agent_service import AgentService

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.post("/me", status_code=status.HTTP_201_CREATED, response_model=APIResponse[AgentProfileDetailResponse])
async def create_my_agent_profile(
    current_user: CurrentUserDep,
    session: SessionDep,
    user_type: Annotated[UserType, Form(...)],
    business_name: Annotated[str, Form(min_length=2, max_length=160)],
    nin_number: Annotated[str, Form(min_length=2, max_length=120)],
    nin_file: Annotated[UploadFile, File(...)],
    business_phone: Annotated[str | None, Form(max_length=32)] = None,
    business_email: Annotated[str | None, Form(max_length=255)] = None,
    license_number: Annotated[str | None, Form(max_length=100)] = None,
    address: Annotated[str | None, Form()] = None,
    city: Annotated[str | None, Form(max_length=100)] = None,
    state: Annotated[str | None, Form(max_length=100)] = None,
    country: Annotated[str, Form(max_length=100)] = "Nigeria",
    cac_number: Annotated[str | None, Form(max_length=120)] = None,
    cac_file: Annotated[UploadFile | None, File()] = None,
    scum_number: Annotated[str | None, Form(max_length=120)] = None,
    scum_file: Annotated[UploadFile | None, File()] = None,
) -> APIResponse[AgentProfileDetailResponse]:
    agent = await AgentService(session).create_my_agent_profile(current_user, user_type=user_type, business_name=business_name, business_phone=business_phone, business_email=business_email, license_number=license_number, address=address, city=city, state=state, country=country, nin_number=nin_number, nin_file=nin_file, cac_number=cac_number, cac_file=cac_file, scum_number=scum_number, scum_file=scum_file)
    return APIResponse(message="Agent profile submitted for review", data=AgentProfileDetailResponse.model_validate(agent))


@router.get("/me", response_model=APIResponse[AgentProfileDetailResponse])
async def get_my_agent_profile(current_user: CurrentUserDep, session: SessionDep) -> APIResponse[AgentProfileDetailResponse]:
    agent = await AgentService(session).get_my_agent_profile(current_user)
    return APIResponse(message="Agent profile", data=AgentProfileDetailResponse.model_validate(agent))


@router.patch("/me", response_model=APIResponse[AgentProfileResponse])
async def update_my_agent_profile(payload: AgentProfileUpdate, current_user: CurrentUserDep, session: SessionDep) -> APIResponse[AgentProfileResponse]:
    agent = await AgentService(session).update_my_agent_profile(current_user, payload)
    return APIResponse(message="Agent profile updated", data=AgentProfileResponse.model_validate(agent))
