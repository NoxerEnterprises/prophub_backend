from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import AgentStatus, TransactionProvider, TransactionStatus, TransactionType, UserRole
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.security import now_utc
from app.models.transaction import Transaction
from app.models.user import User
from app.repositories.transaction_repository import TransactionRepository
from app.services.agent_service import AgentService
from app.services.paystack_service import PaystackService


class PaymentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.transactions = TransactionRepository(session)

    async def initialize_agent_verification_payment(self, *, current_user: User, callback_url: str | None = None) -> Transaction:
        if current_user.role != UserRole.AGENT.value:
            raise ForbiddenError("Only agent accounts can initialize verification payment")
        agent = await AgentService(self.session).get_my_agent_profile(current_user)
        if agent.status == AgentStatus.APPROVED.value:
            raise BadRequestError("Agent is already approved")
        if agent.status == AgentStatus.PAID.value:
            raise BadRequestError("Agent payment has already been completed and is awaiting approval")
        if agent.status == AgentStatus.DISABLED.value:
            raise ForbiddenError("Disabled agents cannot make payment")
        if settings.AGENT_VERIFICATION_FEE <= 0:
            raise BadRequestError("AGENT_VERIFICATION_FEE is not configured")

        existing = await self.transactions.get_pending_agent_verification(agent.id)
        if existing and existing.authorization_url:
            return existing

        reference = f"PROHUB_AGT_{uuid.uuid4().hex[:20].upper()}"
        transaction = Transaction(
            user_id=current_user.id,
            agent_id=agent.id,
            provider=TransactionProvider.PAYSTACK.value,
            payment_type=TransactionType.AGENT_VERIFICATION.value,
            reference=reference,
            amount=settings.AGENT_VERIFICATION_FEE,
            currency=settings.PAYSTACK_CURRENCY,
            status=TransactionStatus.PENDING.value,
            provider_response={},
        )
        await self.transactions.add(transaction)
        await self.session.flush()

        response = await PaystackService().initialize_transaction(
            email=current_user.email,
            amount_minor_units=settings.paystack_amount_minor_units,
            reference=reference,
            currency=settings.PAYSTACK_CURRENCY,
            callback_url=callback_url or settings.PAYSTACK_CALLBACK_URL or None,
            metadata={
                "transaction_id": str(transaction.id),
                "agent_id": str(agent.id),
                "user_id": str(current_user.id),
                "payment_type": TransactionType.AGENT_VERIFICATION.value,
            },
        )
        paystack_data = response.get("data") or {}
        transaction.authorization_url = paystack_data.get("authorization_url")
        transaction.access_code = paystack_data.get("access_code")
        transaction.provider_response = response
        await self.session.commit()
        await self.session.refresh(transaction)
        return transaction

    async def verify_agent_payment(self, *, reference: str, current_user: User | None = None) -> Transaction:
        transaction = await self.transactions.get_by_reference(reference)
        if not transaction:
            raise NotFoundError("Transaction not found")
        if current_user is not None and transaction.user_id != current_user.id:
            raise ForbiddenError("You cannot verify another user's transaction")

        response = await PaystackService().verify_transaction(reference)
        paystack_data = response.get("data") or {}
        return await self._apply_paystack_verification(transaction=transaction, paystack_data=paystack_data, full_response=response)

    async def process_paystack_webhook(self, *, event: dict[str, Any]) -> Transaction | None:
        event_name = event.get("event")
        data = event.get("data") or {}
        reference = data.get("reference")
        if not reference:
            return None
        transaction = await self.transactions.get_by_reference(str(reference))
        if not transaction:
            return None
        if event_name != "charge.success":
            transaction.provider_response = event
            await self.session.commit()
            return transaction
        return await self._apply_paystack_verification(transaction=transaction, paystack_data=data, full_response=event)

    async def list_my_transactions(self, *, current_user: User, page: int = 1, limit: int = 20) -> tuple[list[Transaction], int]:
        return await self.transactions.list_by_user(user_id=current_user.id, page=page, limit=limit)

    async def list_admin_transactions(self, *, page: int = 1, limit: int = 20, status: TransactionStatus | None = None) -> tuple[list[Transaction], int]:
        return await self.transactions.list_all(page=page, limit=limit, status=status.value if status else None)

    async def _apply_paystack_verification(
        self,
        *,
        transaction: Transaction,
        paystack_data: dict[str, Any],
        full_response: dict[str, Any],
    ) -> Transaction:
        if transaction.status == TransactionStatus.SUCCESS.value:
            return transaction

        paystack_status = str(paystack_data.get("status") or "").lower()
        paid_at = self._parse_paystack_datetime(paystack_data.get("paid_at")) or now_utc()
        amount_minor = int(paystack_data.get("amount") or 0)
        currency = str(paystack_data.get("currency") or transaction.currency).upper()

        transaction.provider_response = full_response
        transaction.verified_at = now_utc()

        if currency != transaction.currency.upper():
            transaction.status = TransactionStatus.FAILED.value
            transaction.failure_reason = "Currency mismatch"
            await self.session.commit()
            raise BadRequestError("Paystack currency mismatch")

        if amount_minor != int(transaction.amount * Decimal("100")):
            transaction.status = TransactionStatus.FAILED.value
            transaction.failure_reason = "Amount mismatch"
            await self.session.commit()
            raise BadRequestError("Paystack amount mismatch")

        if paystack_status == "success":
            transaction.status = TransactionStatus.SUCCESS.value
            transaction.failure_reason = None
            transaction.paid_at = paid_at
            if transaction.agent.status in {AgentStatus.PENDING.value, AgentStatus.REJECTED.value}:
                transaction.agent.previous_status = transaction.agent.status
                transaction.agent.status = AgentStatus.PAID.value
                transaction.agent.status_note = "Agent verification payment confirmed via Paystack. Awaiting admin approval."
        elif paystack_status in {"abandoned", "failed", "ongoing", "pending"}:
            transaction.status = self._map_paystack_status(paystack_status).value
            transaction.failure_reason = paystack_data.get("gateway_response") or paystack_data.get("message")
        else:
            transaction.status = TransactionStatus.FAILED.value
            transaction.failure_reason = f"Unsupported Paystack status: {paystack_status}"

        await self.session.commit()
        await self.session.refresh(transaction, attribute_names=["agent", "user"])
        return transaction

    @staticmethod
    def _map_paystack_status(status: str) -> TransactionStatus:
        mapping = {
            "abandoned": TransactionStatus.ABANDONED,
            "failed": TransactionStatus.FAILED,
            "ongoing": TransactionStatus.ONGOING,
            "pending": TransactionStatus.PENDING,
            "success": TransactionStatus.SUCCESS,
        }
        return mapping.get(status.lower(), TransactionStatus.FAILED)

    @staticmethod
    def _parse_paystack_datetime(value: Any) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
