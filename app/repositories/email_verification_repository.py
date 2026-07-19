from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import now_utc
from app.models.email_verification_token import EmailVerificationToken


class EmailVerificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, token: EmailVerificationToken) -> EmailVerificationToken:
        self.session.add(token)
        await self.session.flush()
        return token

    async def mark_all_user_tokens_used(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            update(EmailVerificationToken)
            .where(EmailVerificationToken.user_id == user_id, EmailVerificationToken.used_at.is_(None))
            .values(used_at=now_utc())
        )

    async def get_active_by_token_hash(self, token_hash: str) -> EmailVerificationToken | None:
        result = await self.session.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token_hash == token_hash,
                EmailVerificationToken.used_at.is_(None),
                EmailVerificationToken.expires_at > now_utc(),
            )
        )
        return result.scalar_one_or_none()

    async def get_latest_active_for_user(self, user_id: uuid.UUID) -> EmailVerificationToken | None:
        result = await self.session.execute(
            select(EmailVerificationToken)
            .where(EmailVerificationToken.user_id == user_id, EmailVerificationToken.used_at.is_(None), EmailVerificationToken.expires_at > now_utc())
            .order_by(EmailVerificationToken.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
