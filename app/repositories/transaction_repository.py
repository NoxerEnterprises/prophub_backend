from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import TransactionStatus, TransactionType
from app.models.transaction import Transaction


class TransactionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, transaction: Transaction) -> Transaction:
        self.session.add(transaction)
        await self.session.flush()
        return transaction

    async def get_by_reference(self, reference: str) -> Transaction | None:
        statement = (
            select(Transaction)
            .where(Transaction.reference == reference)
            .options(selectinload(Transaction.agent), selectinload(Transaction.user))
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_pending_agent_verification(self, agent_id: uuid.UUID) -> Transaction | None:
        statement = (
            select(Transaction)
            .where(
                Transaction.agent_id == agent_id,
                Transaction.payment_type == TransactionType.AGENT_VERIFICATION.value,
                Transaction.status == TransactionStatus.PENDING.value,
            )
            .order_by(Transaction.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_user(self, *, user_id: uuid.UUID, page: int = 1, limit: int = 20) -> tuple[list[Transaction], int]:
        base = select(Transaction).where(Transaction.user_id == user_id)
        count = await self.session.execute(select(func.count()).select_from(base.subquery()))
        total = int(count.scalar_one() or 0)
        result = await self.session.execute(base.order_by(Transaction.created_at.desc()).offset((page - 1) * limit).limit(limit))
        return list(result.scalars().all()), total

    async def list_all(self, *, page: int = 1, limit: int = 20, status: str | None = None) -> tuple[list[Transaction], int]:
        base = select(Transaction)
        if status:
            base = base.where(Transaction.status == status)
        count = await self.session.execute(select(func.count()).select_from(base.subquery()))
        total = int(count.scalar_one() or 0)
        result = await self.session.execute(
            base.options(selectinload(Transaction.agent), selectinload(Transaction.user))
            .order_by(Transaction.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        return list(result.scalars().unique().all()), total
