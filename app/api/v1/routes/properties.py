from __future__ import annotations

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.api.dependencies import SessionDep, require_approved_agent
from app.core.enums import ListingType, PropertyCategory, PropertySort, PropertyStatus
from app.models.agent_profile import AgentProfile
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.schemas.property import PropertyCreate, PropertyMediaResponse, PropertyResponse, PropertyUpdate
from app.services.agent_service import AgentService
from app.services.property_service import PropertyService

router = APIRouter(prefix="/properties", tags=["Properties"])
ApprovedAgentDep = Annotated[User, Depends(require_approved_agent)]


async def _approved_agent_profile(current_user: User, session: SessionDep) -> AgentProfile:
    return await AgentService(session).get_my_agent_profile(current_user)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=APIResponse[PropertyResponse])
async def create_property(
    payload: PropertyCreate,
    current_user: ApprovedAgentDep,
    session: SessionDep,
) -> APIResponse[PropertyResponse]:
    agent = await _approved_agent_profile(current_user, session)
    property_obj = await PropertyService(session).create_property(agent=agent, payload=payload)
    return APIResponse(message="Property created", data=PropertyResponse.model_validate(property_obj))


@router.get("", response_model=APIResponse[PaginatedResponse[PropertyResponse]])
async def list_public_properties(
    session: SessionDep,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> APIResponse[PaginatedResponse[PropertyResponse]]:
    properties, total = await PropertyService(session).list_public_properties(page=page, limit=limit)
    return APIResponse(
        message="Properties retrieved",
        data=PaginatedResponse(
            items=[PropertyResponse.model_validate(property_obj) for property_obj in properties],
            meta=PaginationMeta(page=page, limit=limit, total=total),
        ),
    )


@router.get("/search", response_model=APIResponse[PaginatedResponse[PropertyResponse]])
async def search_public_properties(
    session: SessionDep,
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
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> APIResponse[PaginatedResponse[PropertyResponse]]:
    properties, total = await PropertyService(session).search_public_properties(
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
    )
    return APIResponse(
        message="Properties search completed",
        data=PaginatedResponse(
            items=[PropertyResponse.model_validate(property_obj) for property_obj in properties],
            meta=PaginationMeta(page=page, limit=limit, total=total),
        ),
    )


@router.get("/{property_id}", response_model=APIResponse[PropertyResponse])
async def get_public_property(property_id: UUID, session: SessionDep) -> APIResponse[PropertyResponse]:
    property_obj = await PropertyService(session).get_public_property(property_id)
    return APIResponse(message="Property retrieved", data=PropertyResponse.model_validate(property_obj))


@router.patch("/{property_id}", response_model=APIResponse[PropertyResponse])
async def update_property(
    property_id: UUID,
    payload: PropertyUpdate,
    current_user: ApprovedAgentDep,
    session: SessionDep,
) -> APIResponse[PropertyResponse]:
    agent = await _approved_agent_profile(current_user, session)
    property_obj = await PropertyService(session).update_my_property(property_id=property_id, agent=agent, payload=payload)
    return APIResponse(message="Property updated", data=PropertyResponse.model_validate(property_obj))


@router.delete("/{property_id}", response_model=APIResponse[dict[str, bool]])
async def delete_property(
    property_id: UUID,
    current_user: ApprovedAgentDep,
    session: SessionDep,
) -> APIResponse[dict[str, bool]]:
    agent = await _approved_agent_profile(current_user, session)
    await PropertyService(session).soft_delete_my_property(property_id=property_id, agent=agent)
    return APIResponse(message="Property deleted", data={"deleted": True})


@router.post("/{property_id}/media", status_code=status.HTTP_201_CREATED, response_model=APIResponse[PropertyMediaResponse])
async def upload_property_image(
    property_id: UUID,
    current_user: ApprovedAgentDep,
    session: SessionDep,
    file: UploadFile = File(...),
    position: int = Query(default=0, ge=0),
) -> APIResponse[PropertyMediaResponse]:
    agent = await _approved_agent_profile(current_user, session)
    media = await PropertyService(session).upload_property_image(property_id=property_id, agent=agent, file=file, position=position)
    return APIResponse(message="Property image uploaded", data=PropertyMediaResponse.model_validate(media))


@router.delete("/{property_id}/media/{media_id}", response_model=APIResponse[dict[str, bool]])
async def delete_property_image(
    property_id: UUID,
    media_id: UUID,
    current_user: ApprovedAgentDep,
    session: SessionDep,
) -> APIResponse[dict[str, bool]]:
    agent = await _approved_agent_profile(current_user, session)
    await PropertyService(session).delete_property_image(property_id=property_id, media_id=media_id, agent=agent)
    return APIResponse(message="Property image deleted", data={"deleted": True})
