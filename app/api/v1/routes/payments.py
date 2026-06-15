from __future__ import annotations

import json

from fastapi import APIRouter, Query, Request, status

from app.api.dependencies import CurrentUserDep, SessionDep
from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.schemas.payment import PaymentInitializeRequest, PaymentInitializeResponse, PaymentVerifyResponse, TransactionResponse
from app.services.payment_service import PaymentService
from app.services.paystack_service import PaystackService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/initialize", status_code=status.HTTP_201_CREATED, response_model=APIResponse[PaymentInitializeResponse])
async def initialize_payment(
    payload: PaymentInitializeRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> APIResponse[PaymentInitializeResponse]:
    transaction = await PaymentService(session).initialize_agent_verification_payment(
        current_user=current_user,
        callback_url=str(payload.callback_url) if payload.callback_url else None,
    )
    return APIResponse(
        message="Payment initialized",
        data=PaymentInitializeResponse(
            reference=transaction.reference,
            amount=transaction.amount,
            currency=transaction.currency,
            authorization_url=transaction.authorization_url or "",
            access_code=transaction.access_code,
            public_key=settings.PAYSTACK_PUBLIC_KEY or None,
        ),
    )


@router.get("/verify/{reference}", response_model=APIResponse[PaymentVerifyResponse])
async def verify_payment(reference: str, current_user: CurrentUserDep, session: SessionDep) -> APIResponse[PaymentVerifyResponse]:
    transaction = await PaymentService(session).verify_agent_payment(reference=reference, current_user=current_user)
    return APIResponse(
        message="Payment verified",
        data=PaymentVerifyResponse(transaction=TransactionResponse.model_validate(transaction), agent_status=transaction.agent.status),
    )


@router.post("/webhook", response_model=APIResponse[dict[str, bool]])
async def paystack_webhook(request: Request, session: SessionDep) -> APIResponse[dict[str, bool]]:
    raw_body = await request.body()
    signature = request.headers.get("x-paystack-signature")
    if not PaystackService().verify_webhook_signature(raw_body=raw_body, signature=signature):
        raise UnauthorizedError("Invalid Paystack webhook signature")
    try:
        event = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise UnauthorizedError("Invalid webhook payload") from exc

    await PaymentService(session).process_paystack_webhook(event=event)
    return APIResponse(message="Webhook processed", data={"processed": True})


@router.get("/me", response_model=APIResponse[PaginatedResponse[TransactionResponse]])
async def list_my_payments(
    current_user: CurrentUserDep,
    session: SessionDep,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> APIResponse[PaginatedResponse[TransactionResponse]]:
    transactions, total = await PaymentService(session).list_my_transactions(current_user=current_user, page=page, limit=limit)
    return APIResponse(
        message="Payments retrieved",
        data=PaginatedResponse(
            items=[TransactionResponse.model_validate(transaction) for transaction in transactions],
            meta=PaginationMeta(page=page, limit=limit, total=total),
        ),
    )
