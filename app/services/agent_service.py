from __future__ import annotations

import uuid
from datetime import UTC, datetime
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AdminAction, AgentStatus, DocumentType, OperatingMode, SubscriptionStatus, UserRole, UserType
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.security import now_utc
from app.models.agent_profile import AgentProfile
from app.models.user import User
from app.repositories.agent_repository import AgentRepository
from app.repositories.document_repository import DocumentRepository
from app.schemas.agent import AgentProfileUpdate
from app.services.admin_activity_service import AdminActivityService
from app.services.document_service import DocumentService


class AgentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.agents = AgentRepository(session)
        self.documents = DocumentRepository(session)
        self.activity = AdminActivityService(session)

    async def create_my_agent_profile(
        self,
        user: User,
        *,
        user_type: UserType,
        business_name: str,
        business_phone: str | None,
        business_email: str | None,
        license_number: str | None,
        address: str | None,
        city: str | None,
        state: str | None,
        country: str,
        nin_number: str,
        nin_file: UploadFile,
        cac_number: str | None = None,
        cac_file: UploadFile | None = None,
        scum_number: str | None = None,
        scum_file: UploadFile | None = None,
    ) -> AgentProfile:
        if not user.is_email_verified:
            raise ForbiddenError("Email verification required before becoming an agent")
        if user.role in {UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value}:
            raise ForbiddenError("Admin accounts cannot register as agents")
        if user_type == UserType.CUSTOMER:
            raise BadRequestError("Select a non-customer user type to become an agent")
        existing = await self.agents.get_by_user_id(user.id)
        if existing:
            raise ConflictError("Agent profile already exists")
        if (cac_number and not cac_file) or (cac_file and not cac_number):
            raise BadRequestError("CAC number and CAC document upload must be submitted together")
        if (scum_number and not scum_file) or (scum_file and not scum_number):
            raise BadRequestError("SCUM number and SCUM document upload must be submitted together")

        user.role = UserRole.AGENT.value
        user.user_type = user_type.value
        agent = AgentProfile(
            user_id=user.id,
            user_type=user_type.value,
            operating_mode=OperatingMode.NOXER_MANAGED.value,
            business_name=business_name.strip(),
            business_phone=business_phone,
            business_email=business_email,
            license_number=license_number,
            address=address,
            city=city,
            state=state,
            country=country or "Nigeria",
            status=AgentStatus.PENDING.value,
            subscription_status=SubscriptionStatus.INACTIVE.value,
        )
        await self.agents.add(agent)
        document_service = DocumentService(self.session)
        await document_service.upsert_agent_document(user=user, agent=agent, document_type=DocumentType.NIN, document_number=nin_number, file=nin_file)
        if cac_number and cac_file:
            await document_service.upsert_agent_document(user=user, agent=agent, document_type=DocumentType.CAC, document_number=cac_number, file=cac_file)
        if scum_number and scum_file:
            await document_service.upsert_agent_document(user=user, agent=agent, document_type=DocumentType.SCUM, document_number=scum_number, file=scum_file)
        await self.session.commit()
        await self.session.refresh(agent, attribute_names=["user", "documents"])
        return agent

    async def get_my_agent_profile(self, user: User) -> AgentProfile:
        agent = await self.agents.get_by_user_id(user.id)
        if not agent:
            raise NotFoundError("Agent profile not found")
        return agent

    async def update_my_agent_profile(self, user: User, payload: AgentProfileUpdate) -> AgentProfile:
        if not user.is_email_verified:
            raise ForbiddenError("Email verification required")
        agent = await self.agents.get_by_user_id(user.id)
        if not agent:
            raise NotFoundError("Agent profile not found")
        if agent.status == AgentStatus.DISABLED.value:
            raise ForbiddenError("Disabled agents cannot update profile")
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(agent, field, str(value) if field == "business_email" and value else value)
        await self.session.commit()
        await self.session.refresh(agent, attribute_names=["user", "documents"])
        return agent

    async def list_agents(self, *, page: int = 1, limit: int = 20, status: AgentStatus | None = None, q: str | None = None, user_type: UserType | None = None, operating_mode: OperatingMode | None = None, subscription_status: SubscriptionStatus | None = None):
        return await self.agents.list_agents(page=page, limit=limit, status=status.value if status else None, q=q, user_type=user_type.value if user_type else None, operating_mode=operating_mode.value if operating_mode else None, subscription_status=subscription_status.value if subscription_status else None)

    async def get_agent_for_admin(self, agent_id: uuid.UUID) -> AgentProfile:
        agent = await self.agents.get_by_id(agent_id)
        if not agent:
            raise NotFoundError("Agent not found")
        return agent

    async def is_agent_subscription_active(self, agent: AgentProfile) -> bool:
        if agent.subscription_status != SubscriptionStatus.ACTIVE.value or not agent.subscription_expires_at:
            return False
        expires = agent.subscription_expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return expires > now_utc()

    async def can_agent_post(self, agent: AgentProfile) -> bool:
        nin = await self.documents.get_agent_document(agent_profile_id=agent.id, document_type=DocumentType.NIN.value)
        return bool(agent.status == AgentStatus.APPROVED.value and nin and nin.status == "APPROVED" and await self.is_agent_subscription_active(agent))

    async def approve_agent(self, *, agent_id: UUID, admin: User, note: str | None = None, allow_override: bool = False, allow_unpaid_override: bool = False) -> AgentProfile:
        agent = await self.get_agent_for_admin(agent_id)
        override = allow_override or allow_unpaid_override
        if agent.status == AgentStatus.APPROVED.value:
            return agent
        if agent.status == AgentStatus.DISABLED.value:
            raise BadRequestError("Disabled agent must be enabled before approval")
        nin = await self.documents.get_agent_document(agent_profile_id=agent.id, document_type=DocumentType.NIN.value)
        if not override and not (nin and nin.status == "APPROVED"):
            raise BadRequestError("NIN document must be approved before agent approval")
        if not override and not await self.is_agent_subscription_active(agent):
            raise BadRequestError("Agent must have an active subscription before approval")
        old_status = agent.status
        agent.status = AgentStatus.APPROVED.value
        agent.previous_status = old_status
        agent.status_note = note
        agent.approved_at = now_utc()
        agent.approved_by = admin.id
        await self.activity.log(admin_id=admin.id, action=AdminAction.AGENT_APPROVED.value, target_type="agent_profile", target_id=agent.id, description=note, metadata={"old_status": old_status, "new_status": agent.status, "allow_override": override})
        await self.session.commit()
        await self.session.refresh(agent, attribute_names=["user", "documents"])
        return agent

    async def reject_agent(self, *, agent_id: UUID, admin: User, note: str | None = None) -> AgentProfile:
        agent = await self.get_agent_for_admin(agent_id)
        if agent.status == AgentStatus.DISABLED.value:
            raise BadRequestError("Disabled agent must be enabled before rejection")
        old_status = agent.status
        agent.status = AgentStatus.REJECTED.value
        agent.previous_status = old_status
        agent.status_note = note
        agent.rejected_at = now_utc()
        agent.rejected_by = admin.id
        await self.activity.log(admin_id=admin.id, action=AdminAction.AGENT_REJECTED.value, target_type="agent_profile", target_id=agent.id, description=note, metadata={"old_status": old_status, "new_status": agent.status})
        await self.session.commit()
        await self.session.refresh(agent, attribute_names=["user", "documents"])
        return agent

    async def disable_agent(self, *, agent_id: UUID, admin: User, note: str | None = None) -> AgentProfile:
        agent = await self.get_agent_for_admin(agent_id)
        if agent.status == AgentStatus.DISABLED.value:
            return agent
        old_status = agent.status
        agent.previous_status = old_status
        agent.status = AgentStatus.DISABLED.value
        agent.status_note = note
        agent.disabled_at = now_utc()
        agent.disabled_by = admin.id
        await self.activity.log(admin_id=admin.id, action=AdminAction.AGENT_DISABLED.value, target_type="agent_profile", target_id=agent.id, description=note, metadata={"old_status": old_status, "new_status": agent.status})
        await self.session.commit()
        await self.session.refresh(agent, attribute_names=["user", "documents"])
        return agent

    async def enable_agent(self, *, agent_id: UUID, admin: User, note: str | None = None) -> AgentProfile:
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
        await self.activity.log(admin_id=admin.id, action=AdminAction.AGENT_ENABLED.value, target_type="agent_profile", target_id=agent.id, description=note, metadata={"old_status": old_status, "new_status": agent.status})
        await self.session.commit()
        await self.session.refresh(agent, attribute_names=["user", "documents"])
        return agent
