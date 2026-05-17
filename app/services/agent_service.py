from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AdminAction, AgentStatus, UserRole
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.security import now_utc
from app.models.agent_profile import AgentProfile
from app.models.user import User
from app.repositories.agent_repository import AgentRepository
from app.schemas.agent import AgentProfileCreate, AgentProfileUpdate
from app.services.admin_activity_service import AdminActivityService


class AgentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.agents = AgentRepository(session)
        self.activity = AdminActivityService(session)

    async def create_my_agent_profile(self, user: User, payload: AgentProfileCreate) -> AgentProfile:
        if user.role in {UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value}:
            raise ForbiddenError("Admin accounts cannot register as agents")
        existing = await self.agents.get_by_user_id(user.id)
        if existing:
            raise ConflictError("Agent profile already exists")

        user.role = UserRole.AGENT.value
        agent = AgentProfile(
            user_id=user.id,
            business_name=payload.business_name.strip(),
            business_phone=payload.business_phone,
            business_email=str(payload.business_email) if payload.business_email else None,
            license_number=payload.license_number,
            address=payload.address,
            city=payload.city,
            state=payload.state,
            country=payload.country,
            status=AgentStatus.PENDING.value,
        )
        await self.agents.add(agent)
        await self.session.commit()
        await self.session.refresh(agent, attribute_names=["user"])
        return agent

    async def get_my_agent_profile(self, user: User) -> AgentProfile:
        agent = await self.agents.get_by_user_id(user.id)
        if not agent:
            raise NotFoundError("Agent profile not found")
        return agent

    async def update_my_agent_profile(self, user: User, payload: AgentProfileUpdate) -> AgentProfile:
        agent = await self.agents.get_by_user_id(user.id)
        if not agent:
            raise NotFoundError("Agent profile not found")
        if agent.status == AgentStatus.DISABLED.value:
            raise ForbiddenError("Disabled agents cannot update profile")

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(agent, field, str(value) if field == "business_email" and value else value)
        await self.session.commit()
        await self.session.refresh(agent, attribute_names=["user"])
        return agent

    async def list_agents(self, *, page: int = 1, limit: int = 20, status: AgentStatus | None = None, q: str | None = None):
        return await self.agents.list_agents(page=page, limit=limit, status=status.value if status else None, q=q)

    async def get_agent_for_admin(self, agent_id: uuid.UUID) -> AgentProfile:
        agent = await self.agents.get_by_id(agent_id)
        if not agent:
            raise NotFoundError("Agent not found")
        return agent

    async def approve_agent(self, *, agent_id: uuid.UUID, admin: User, note: str | None = None, allow_unpaid_override: bool = False) -> AgentProfile:
        agent = await self.get_agent_for_admin(agent_id)
        if agent.status == AgentStatus.APPROVED.value:
            return agent
        if agent.status == AgentStatus.DISABLED.value:
            raise BadRequestError("Disabled agent must be enabled before approval")
        if agent.status != AgentStatus.PAID.value and not allow_unpaid_override:
            raise BadRequestError("Only PAID agents can be approved. Use override only for development/manual exception.")

        old_status = agent.status
        agent.status = AgentStatus.APPROVED.value
        agent.previous_status = old_status
        agent.status_note = note
        agent.approved_at = now_utc()
        agent.approved_by = admin.id
        await self.activity.log(
            admin_id=admin.id,
            action=AdminAction.AGENT_APPROVED.value,
            target_type="agent_profile",
            target_id=agent.id,
            description=note,
            metadata={"old_status": old_status, "new_status": agent.status, "allow_unpaid_override": allow_unpaid_override},
        )
        await self.session.commit()
        await self.session.refresh(agent, attribute_names=["user"])
        return agent

    async def reject_agent(self, *, agent_id: uuid.UUID, admin: User, note: str | None = None) -> AgentProfile:
        agent = await self.get_agent_for_admin(agent_id)
        if agent.status == AgentStatus.DISABLED.value:
            raise BadRequestError("Disabled agent must be enabled before rejection")
        old_status = agent.status
        agent.status = AgentStatus.REJECTED.value
        agent.previous_status = old_status
        agent.status_note = note
        agent.rejected_at = now_utc()
        agent.rejected_by = admin.id
        await self.activity.log(
            admin_id=admin.id,
            action=AdminAction.AGENT_REJECTED.value,
            target_type="agent_profile",
            target_id=agent.id,
            description=note,
            metadata={"old_status": old_status, "new_status": agent.status},
        )
        await self.session.commit()
        await self.session.refresh(agent, attribute_names=["user"])
        return agent

    async def disable_agent(self, *, agent_id: uuid.UUID, admin: User, note: str | None = None) -> AgentProfile:
        agent = await self.get_agent_for_admin(agent_id)
        if agent.status == AgentStatus.DISABLED.value:
            return agent
        old_status = agent.status
        agent.previous_status = old_status
        agent.status = AgentStatus.DISABLED.value
        agent.status_note = note
        agent.disabled_at = now_utc()
        agent.disabled_by = admin.id
        await self.activity.log(
            admin_id=admin.id,
            action=AdminAction.AGENT_DISABLED.value,
            target_type="agent_profile",
            target_id=agent.id,
            description=note,
            metadata={"old_status": old_status, "new_status": agent.status},
        )
        await self.session.commit()
        await self.session.refresh(agent, attribute_names=["user"])
        return agent

    async def enable_agent(self, *, agent_id: uuid.UUID, admin: User, note: str | None = None) -> AgentProfile:
        agent = await self.get_agent_for_admin(agent_id)
        if agent.status != AgentStatus.DISABLED.value:
            return agent
        old_status = agent.status
        restored_status = agent.previous_status or AgentStatus.PENDING.value
        agent.status = restored_status
        agent.previous_status = old_status
        agent.status_note = note
        agent.disabled_at = None
        agent.disabled_by = None
        await self.activity.log(
            admin_id=admin.id,
            action=AdminAction.AGENT_ENABLED.value,
            target_type="agent_profile",
            target_id=agent.id,
            description=note,
            metadata={"old_status": old_status, "new_status": agent.status},
        )
        await self.session.commit()
        await self.session.refresh(agent, attribute_names=["user"])
        return agent
