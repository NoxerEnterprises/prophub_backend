from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC
from typing import Annotated
import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AgentStatus, DocumentType, SubscriptionStatus, TokenType, UserRole
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_jwt_token, now_utc
from app.db.session import get_async_session
from app.models.user import User
from app.repositories.document_repository import DocumentRepository
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)
SessionDep = Annotated[AsyncSession, Depends(get_async_session)]


async def get_current_user(session: SessionDep, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]) -> User:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Bearer access token is required")
    try:
        payload = decode_jwt_token(credentials.credentials, expected_type=TokenType.ACCESS)
        user_id = uuid.UUID(str(payload.get("sub")))
    except (ValueError, TypeError) as exc:
        raise UnauthorizedError("Invalid access token") from exc
    user = await UserRepository(session).get_by_id(user_id)
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    if not user.is_email_verified:
        raise ForbiddenError("Email verification required")
    if user.role == UserRole.AGENT.value and user.agent_profile and user.agent_profile.status == AgentStatus.DISABLED.value:
        raise ForbiddenError("This agent account is disabled")
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_roles(allowed_roles: Sequence[UserRole]) -> Callable[[CurrentUserDep], User]:
    async def role_checker(current_user: CurrentUserDep) -> User:
        if current_user.role not in {role.value for role in allowed_roles}:
            raise ForbiddenError("Insufficient role permission")
        return current_user
    return role_checker


async def require_admin(current_user: CurrentUserDep) -> User:
    if current_user.role not in {UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value}:
        raise ForbiddenError("Admin access required")
    return current_user


async def require_super_admin(current_user: CurrentUserDep) -> User:
    if current_user.role != UserRole.SUPER_ADMIN.value:
        raise ForbiddenError("Super admin access required")
    return current_user


async def require_approved_agent(current_user: CurrentUserDep, session: SessionDep) -> User:
    if current_user.role != UserRole.AGENT.value or not current_user.agent_profile:
        raise ForbiddenError("Agent account required")
    agent = current_user.agent_profile
    if agent.status != AgentStatus.APPROVED.value:
        raise ForbiddenError("Approved agent status required")
    if agent.subscription_status != SubscriptionStatus.ACTIVE.value or not agent.subscription_expires_at:
        raise ForbiddenError("Active subscription required")
    expires = agent.subscription_expires_at.replace(tzinfo=UTC) if agent.subscription_expires_at.tzinfo is None else agent.subscription_expires_at
    if expires <= now_utc():
        raise ForbiddenError("Agent subscription has expired")
    nin = await DocumentRepository(session).get_agent_document(agent_profile_id=agent.id, document_type=DocumentType.NIN.value)
    if not nin or nin.status != "APPROVED":
        raise ForbiddenError("Approved NIN document required")
    return current_user
