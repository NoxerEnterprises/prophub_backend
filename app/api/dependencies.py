from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AgentStatus, TokenType, UserRole
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_jwt_token
from app.db.session import get_async_session
from app.models.user import User
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]


async def get_current_user(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
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


async def require_approved_agent(current_user: CurrentUserDep) -> User:
    if current_user.role != UserRole.AGENT.value or not current_user.agent_profile:
        raise ForbiddenError("Agent account required")
    if current_user.agent_profile.status != AgentStatus.APPROVED.value:
        raise ForbiddenError("Approved agent status required")
    return current_user
