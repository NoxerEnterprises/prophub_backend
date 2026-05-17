from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import now_utc
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken


class TokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_refresh_token(self, token: RefreshToken) -> RefreshToken:
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_active_refresh_token(self, token_hash: str, jti: str) -> RefreshToken | None:
        statement = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.jti == jti,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now_utc(),
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, token: RefreshToken, replaced_by_token_id: uuid.UUID | None = None) -> None:
        token.revoked_at = now_utc()
        token.replaced_by_token_id = replaced_by_token_id
        await self.session.flush()

    async def revoke_all_user_refresh_tokens(self, user_id: uuid.UUID) -> None:
        statement = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now_utc())
        )
        await self.session.execute(statement)

    async def add_password_reset_token(self, token: PasswordResetToken) -> PasswordResetToken:
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_active_password_reset_token(self, token_hash: str) -> PasswordResetToken | None:
        statement = select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now_utc(),
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def mark_reset_token_used(self, token: PasswordResetToken) -> None:
        token.used_at = now_utc()
        await self.session.flush()

    async def mark_all_user_reset_tokens_used(self, user_id: uuid.UUID) -> None:
        statement = (
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user_id, PasswordResetToken.used_at.is_(None))
            .values(used_at=now_utc())
        )
        await self.session.execute(statement)
