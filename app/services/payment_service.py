from __future__ import annotations

import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import AgentStatus, AdminAction, DocumentType, SubscriptionStatus, TransactionProvider, TransactionStatus, TransactionType, UserRole
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.security import now_utc
from app.models.transaction import Transaction
from app.models.user import User
from app.repositories.document_repository import DocumentRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.admin_activity_service import AdminActivityService
from app.services.agent_service import AgentService
from app.services.paystack_service import PaystackService


class PaymentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.transactions = TransactionRepository(session)
        self.documents = DocumentRepository(session)
        self.activity = AdminActivityService(session)

    async def initialize_agent_subscription_payment(self, *, current_user: User, callback_url: str | None = None) -> Transaction:
        if current_user.role != UserRole.AGENT.value:
            raise ForbiddenError("Only agent accounts can initialize subscription payment")
        if not current_user.is_email_verified:
            raise ForbiddenError("Email verification required")
        agent = await AgentService(self.session).get_my_agent_profile(current_user)
        if agent.status == AgentStatus.DISABLED.value:
            raise ForbiddenError("Disabled agents cannot make payment")
        if settings.agent_subscription_fee <= 0:
            raise BadRequestError("AGENT_SUBSCRIPTION_FEE is not configured")
        nin = await self.documents.get_agent_document(agent_profile_id=agent.id, document_type=DocumentType.NIN.value)
        if not nin:
            raise BadRequestError("NIN document is required before subscription payment")
        if await AgentService(self.session).is_agent_subscription_active(agent):
            raise BadRequestError("Agent already has an active subscription")
        existing = await self.transactions.get_pending_agent_subscription(agent.id)
        if existing and existing.authorization_url:
            return existing
        reference = f"PROHUB_SUB_{uuid.uuid4().hex[:20].upper()}"
        transaction = Transaction(user_id=current_user.id, agent_id=agent.id, provider=TransactionProvider.PAYSTACK.value, payment_type=TransactionType.AGENT_SUBSCRIPTION.value, reference=reference, amount=settings.agent_subscription_fee, currency=settings.PAYSTACK_CURRENCY, status=TransactionStatus.PENDING.value, subscription_duration_months=settings.SUBSCRIPTION_DURATION_MONTHS, provider_response={})
        await self.transactions.add(transaction)
        await self.session.flush()
        response = await PaystackService().initialize_transaction(email=current_user.email, amount_minor_units=settings.paystack_amount_minor_units, reference=reference, currency=settings.PAYSTACK_CURRENCY, callback_url=callback_url or settings.PAYSTACK_CALLBACK_URL or None, metadata={"transaction_id": str(transaction.id), "agent_id": str(agent.id), "user_id": str(current_user.id), "payment_type": TransactionType.AGENT_SUBSCRIPTION.value, "subscription_duration_months": settings.SUBSCRIPTION_DURATION_MONTHS})
        paystack_data = response.get("data") or {}
        transaction.authorization_url = paystack_data.get("authorization_url")
        transaction.access_code = paystack_data.get("access_code")
        transaction.provider_response = response
        await self.session.commit()
        await self.session.refresh(transaction)
        return transaction

    async def initialize_agent_verification_payment(self, *, current_user: User, callback_url: str | None = None) -> Transaction:
        return await self.initialize_agent_subscription_payment(current_user=current_user, callback_url=callback_url)

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

    async def list_my_transactions(self, *, current_user: User, page: int = 1, limit: int = 20):
        return await self.transactions.list_by_user(user_id=current_user.id, page=page, limit=limit)

    async def list_admin_transactions(self, *, page: int = 1, limit: int = 20, status: TransactionStatus | None = None):
        return await self.transactions.list_all(page=page, limit=limit, status=status.value if status else None)

    async def _apply_paystack_verification(self, *, transaction: Transaction, paystack_data: dict[str, Any], full_response: dict[str, Any]) -> Transaction:
        provider_status = str(paystack_data.get("status") or "").lower()
        transaction.provider_response = full_response
        if transaction.status == TransactionStatus.SUCCESS.value:
            return transaction
        amount_minor = paystack_data.get("amount")
        currency = str(paystack_data.get("currency") or transaction.currency).upper()
        expected_minor = int(Decimal(transaction.amount) * Decimal("100"))
        if provider_status == "success" and int(amount_minor or 0) == expected_minor and currency == transaction.currency.upper():
            now = now_utc()
            duration = transaction.subscription_duration_months or settings.SUBSCRIPTION_DURATION_MONTHS
            period_end = now + timedelta(days=duration * 30)
            transaction.status = TransactionStatus.SUCCESS.value
            transaction.paid_at = now
            transaction.verified_at = now
            transaction.subscription_period_start = now
            transaction.subscription_period_end = period_end
            agent = transaction.agent
            agent.previous_status = agent.status
            if agent.status not in {AgentStatus.APPROVED.value, AgentStatus.DISABLED.value}:
                agent.status = AgentStatus.PAID.value
            agent.subscription_status = SubscriptionStatus.ACTIVE.value
            agent.subscription_started_at = now
            agent.subscription_expires_at = period_end
            agent.last_subscription_transaction_id = transaction.id
            await self.activity.log(admin_id=transaction.user_id, action=AdminAction.TRANSACTION_VERIFIED.value, target_type="transaction", target_id=transaction.id, description="Agent subscription payment verified", metadata={"reference": transaction.reference, "duration_months": duration})
        else:
            mapped = self._map_paystack_status(provider_status)
            transaction.status = mapped
            transaction.verified_at = now_utc()
            transaction.failure_reason = f"Paystack status={provider_status}, amount={amount_minor}, currency={currency}"
        await self.session.commit()
        await self.session.refresh(transaction, attribute_names=["agent", "user"])
        return transaction

    @staticmethod
    def _map_paystack_status(status: str) -> str:
        mapping = {"failed": TransactionStatus.FAILED.value, "abandoned": TransactionStatus.ABANDONED.value, "ongoing": TransactionStatus.ONGOING.value, "pending": TransactionStatus.PENDING.value}
        return mapping.get(status, TransactionStatus.FAILED.value)
