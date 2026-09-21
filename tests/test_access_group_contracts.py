from datetime import timedelta
from types import SimpleNamespace

import pytest

from app.core.enums import SubscriptionStatus
from app.core.security import add_months, now_utc
from app.schemas.auth import EmailVerificationRequest
from app.schemas.chat import GroupChatCreateRequest
from app.services.agent_service import AgentService
from app.services.chat_service import ChatService
from app.core.exceptions import BadRequestError


def test_email_verification_accepts_common_otp_aliases():
    assert EmailVerificationRequest(email="user@example.com", otp_code="123456").otp_code == "123456"
    assert EmailVerificationRequest.model_validate({"email": "user@example.com", "otp": "123456"}).otp_code == "123456"
    assert EmailVerificationRequest.model_validate({"email": "user@example.com", "code": "123456"}).otp_code == "123456"


def test_add_months_uses_calendar_months():
    value = now_utc().replace(year=2026, month=1, day=31)
    result = add_months(value, 1)
    assert result.year == 2026
    assert result.month == 2
    assert result.day == 28


@pytest.mark.asyncio
async def test_admin_granted_access_is_treated_as_active():
    service = AgentService(session=None)  # type: ignore[arg-type]
    agent = SimpleNamespace(
        subscription_status=SubscriptionStatus.ADMIN_GRANTED.value,
        subscription_expires_at=now_utc() + timedelta(days=1),
    )
    assert await service.has_active_agent_access(agent) is True


@pytest.mark.asyncio
async def test_revoked_access_is_not_active():
    service = AgentService(session=None)  # type: ignore[arg-type]
    agent = SimpleNamespace(
        subscription_status=SubscriptionStatus.REVOKED.value,
        subscription_expires_at=now_utc() + timedelta(days=365),
    )
    assert await service.has_active_agent_access(agent) is False


def test_group_chat_requires_geographic_state():
    payload = GroupChatCreateRequest(title="Lekki Agents", state="Lagos")
    assert payload.country == "Nigeria"
    assert payload.state == "Lagos"


def test_listing_must_match_group_geography():
    chat = SimpleNamespace(country="Nigeria", state="Lagos", local_government="Eti-Osa", community=None)
    property_obj = SimpleNamespace(country="Nigeria", state="Lagos", local_government="Ikeja", community=None)
    with pytest.raises(BadRequestError):
        ChatService._validate_listing_location(chat=chat, property_obj=property_obj)

def test_admin_grant_defaults_can_cover_twelve_calendar_months():
    service = AgentService(session=None)  # type: ignore[arg-type]
    agent = SimpleNamespace(
        subscription_status=SubscriptionStatus.INACTIVE.value,
        subscription_started_at=None,
        subscription_expires_at=None,
    )
    service._apply_admin_grant(agent, duration_months=12)
    assert agent.subscription_status == SubscriptionStatus.ADMIN_GRANTED.value
    assert agent.subscription_expires_at == add_months(agent.subscription_started_at, 12)
