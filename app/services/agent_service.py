from __future__ import annotations

import uuid
from datetime import UTC
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import (
    AdminAction,
    AgentStatus,
    DocumentStatus,
    DocumentType,
    OperatingMode,
    SubscriptionStatus,
    UserRole,
    UserType,
)
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.security import add_months, now_utc
from app.models.agent_profile import AgentProfile
from app.models.user import User
from app.repositories.agent_repository import AgentRepository
from app.repositories.document_repository import DocumentRepository
from app.schemas.agent import AgentProfileUpdate
from app.services.admin_activity_service import AdminActivityService
from app.services.document_service import DocumentService


class AgentService:
    ACTIVE_ACCESS_STATUSES = {
        SubscriptionStatus.ACTIVE.value,
        SubscriptionStatus.ADMIN_GRANTED.value,
    }

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
        await document_service.upsert_agent_document(
            user=user,
            agent=agent,
            document_type=DocumentType.NIN,
            document_number=nin_number,
            file=nin_file,
        )
        if cac_number and cac_file:
            await document_service.upsert_agent_document(
                user=user,
                agent=agent,
                document_type=DocumentType.CAC,
                document_number=cac_number,
                file=cac_file,
            )
        if scum_number and scum_file:
            await document_service.upsert_agent_document(
                user=user,
                agent=agent,
                document_type=DocumentType.SCUM,
                document_number=scum_number,
                file=scum_file,
            )
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

    async def list_agents(
        self,
        *,
        page: int = 1,
        limit: int = 20,
        status: AgentStatus | None = None,
        q: str | None = None,
        user_type: UserType | None = None,
        operating_mode: OperatingMode | None = None,
        subscription_status: SubscriptionStatus | None = None,
    ):
        return await self.agents.list_agents(
            page=page,
            limit=limit,
            status=status.value if status else None,
            q=q,
            user_type=user_type.value if user_type else None,
            operating_mode=operating_mode.value if operating_mode else None,
            subscription_status=subscription_status.value if subscription_status else None,
        )

    async def get_agent_for_admin(self, agent_id: uuid.UUID) -> AgentProfile:
        agent = await self.agents.get_by_id(agent_id)
        if not agent:
            raise NotFoundError("Agent not found")
        return agent

    @staticmethod
    def _is_future(expiry) -> bool:
        if expiry is None:
            return False
        expires = expiry.replace(tzinfo=UTC) if expiry.tzinfo is None else expiry
        return expires > now_utc()

    async def is_agent_subscription_active(self, agent: AgentProfile) -> bool:
        """True only for a paid, unexpired subscription."""
        return bool(
            agent.subscription_status == SubscriptionStatus.ACTIVE.value
            and self._is_future(agent.subscription_expires_at)
        )

    async def has_active_agent_access(self, agent: AgentProfile) -> bool:
        """Paid and admin-granted access are equivalent for feature authorization."""
        return bool(
            agent.subscription_status in self.ACTIVE_ACCESS_STATUSES
            and self._is_future(agent.subscription_expires_at)
        )

    async def has_approved_nin(self, agent: AgentProfile) -> bool:
        nin = await self.documents.get_agent_document(
            agent_profile_id=agent.id,
            document_type=DocumentType.NIN.value,
        )
        return bool(nin and nin.status == DocumentStatus.APPROVED.value)

    async def can_agent_use_features(self, agent: AgentProfile) -> bool:
        return bool(
            agent.status == AgentStatus.APPROVED.value
            and await self.has_approved_nin(agent)
            and await self.has_active_agent_access(agent)
        )

    async def can_agent_post(self, agent: AgentProfile) -> bool:
        return await self.can_agent_use_features(agent)

    async def require_active_agent_access(self, user: User) -> AgentProfile:
        if user.role != UserRole.AGENT.value:
            raise ForbiddenError("Agent account required")
        agent = await self.agents.get_by_user_id(user.id)
        if not agent:
            raise ForbiddenError("Agent profile required")
        if not await self.can_agent_use_features(agent):
            if agent.status != AgentStatus.APPROVED.value:
                raise ForbiddenError("Approved agent status required")
            if not await self.has_approved_nin(agent):
                raise ForbiddenError("Approved NIN document required")
            raise ForbiddenError("Active paid or admin-granted agent access required")
        return agent

    async def approve_agent(
        self,
        *,
        agent_id: UUID,
        admin: User,
        note: str | None = None,
        allow_override: bool = False,
        allow_unpaid_override: bool = False,
    ) -> AgentProfile:
        agent = await self.get_agent_for_admin(agent_id)
        override_payment = allow_override or allow_unpaid_override
        if agent.status == AgentStatus.DISABLED.value:
            raise BadRequestError("Disabled agent must be enabled before approval")
        if not await self.has_approved_nin(agent):
            raise BadRequestError("NIN document must be approved before agent approval")

        has_access = await self.has_active_agent_access(agent)
        if not has_access and not override_payment:
            raise BadRequestError("Agent must have active paid access, or admin must allow payment override")
        if not has_access and override_payment:
            self._apply_admin_grant(agent, duration_months=12)

        old_status = agent.status
        agent.status = AgentStatus.APPROVED.value
        agent.previous_status = old_status
        agent.status_note = note
        agent.approved_at = now_utc()
        agent.approved_by = admin.id
        agent.rejected_at = None
        agent.rejected_by = None
        await self.activity.log(
            admin_id=admin.id,
            action=AdminAction.AGENT_APPROVED.value,
            target_type="agent_profile",
            target_id=agent.id,
            description=note,
            metadata={
                "old_status": old_status,
                "new_status": agent.status,
                "payment_override": override_payment,
                "subscription_status": agent.subscription_status,
                "subscription_expires_at": agent.subscription_expires_at.isoformat() if agent.subscription_expires_at else None,
            },
        )
        if override_payment and not has_access:
            await self.activity.log(
                admin_id=admin.id,
                action=AdminAction.AGENT_ACCESS_GRANTED.value,
                target_type="agent_profile",
                target_id=agent.id,
                description=note or "Access granted during approval without subscription payment",
                metadata={"duration_months": 12, "expires_at": agent.subscription_expires_at.isoformat()},
            )
        await self.session.commit()
        await self.session.refresh(agent, attribute_names=["user", "documents"])
        return agent

    async def grant_access(
        self,
        *,
        agent_id: UUID,
        admin: User,
        duration_months: int = 12,
        note: str | None = None,
    ) -> AgentProfile:
        agent = await self.get_agent_for_admin(agent_id)
        if agent.status != AgentStatus.APPROVED.value:
            raise BadRequestError("Agent must be approved before manual access can be granted")
        if not await self.has_approved_nin(agent):
            raise BadRequestError("NIN document must be approved before access can be granted")
        if await self.has_active_agent_access(agent):
            raise BadRequestError("Agent already has active paid or admin-granted access")
        self._apply_admin_grant(agent, duration_months=duration_months)
        await self.activity.log(
            admin_id=admin.id,
            action=AdminAction.AGENT_ACCESS_GRANTED.value,
            target_type="agent_profile",
            target_id=agent.id,
            description=note,
            metadata={
                "duration_months": duration_months,
                "expires_at": agent.subscription_expires_at.isoformat(),
            },
        )
        await self.session.commit()
        await self.session.refresh(agent, attribute_names=["user", "documents"])
        return agent

    def _apply_admin_grant(self, agent: AgentProfile, *, duration_months: int) -> None:
        now = now_utc()
        agent.subscription_status = SubscriptionStatus.ADMIN_GRANTED.value
        agent.subscription_started_at = now
        agent.subscription_expires_at = add_months(now, duration_months)

    async def revoke_access(self, *, agent_id: UUID, admin: User, note: str | None = None) -> AgentProfile:
        agent = await self.get_agent_for_admin(agent_id)
        old_access = agent.subscription_status
        agent.subscription_status = SubscriptionStatus.REVOKED.value
        agent.subscription_expires_at = now_utc()
        await self.activity.log(
            admin_id=admin.id,
            action=AdminAction.AGENT_ACCESS_REVOKED.value,
            target_type="agent_profile",
            target_id=agent.id,
            description=note,
            metadata={"old_subscription_status": old_access, "new_subscription_status": agent.subscription_status},
        )
        await self.session.commit()
        await self.session.refresh(agent, attribute_names=["user", "documents"])
        return agent

    async def step_down_agent(self, *, agent_id: UUID, admin: User, note: str | None = None) -> AgentProfile:
        agent = await self.get_agent_for_admin(agent_id)
        if agent.status == AgentStatus.DISABLED.value:
            raise BadRequestError("Disabled agent must be enabled before stepping down")
        old_status = agent.status
        old_access = agent.subscription_status
        agent.previous_status = old_status
        agent.status = AgentStatus.PENDING.value
        agent.status_note = note
        agent.subscription_status = SubscriptionStatus.REVOKED.value
        agent.subscription_expires_at = now_utc()
        agent.approved_at = None
        agent.approved_by = None
        await self.activity.log(
            admin_id=admin.id,
            action=AdminAction.AGENT_STEPPED_DOWN.value,
            target_type="agent_profile",
            target_id=agent.id,
            description=note,
            metadata={
                "old_status": old_status,
                "new_status": agent.status,
                "old_subscription_status": old_access,
                "new_subscription_status": agent.subscription_status,
            },
        )
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
        await self.activity.log(
            admin_id=admin.id,
            action=AdminAction.AGENT_REJECTED.value,
            target_type="agent_profile",
            target_id=agent.id,
            description=note,
            metadata={"old_status": old_status, "new_status": agent.status},
        )
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
        await self.activity.log(
            admin_id=admin.id,
            action=AdminAction.AGENT_DISABLED.value,
            target_type="agent_profile",
            target_id=agent.id,
            description=note,
            metadata={"old_status": old_status, "new_status": agent.status},
        )
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
        await self.activity.log(
            admin_id=admin.id,
            action=AdminAction.AGENT_ENABLED.value,
            target_type="agent_profile",
            target_id=agent.id,
            description=note,
            metadata={"old_status": old_status, "new_status": agent.status},
        )
        await self.session.commit()
        await self.session.refresh(agent, attribute_names=["user", "documents"])
        return agent
