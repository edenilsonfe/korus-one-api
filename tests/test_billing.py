"""Billing webhook and reconciliation tests."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.billing.types import InternalBillingEventType
from app.billing.webhook_normalizer import StubWebhookNormalizer
from app.models.billing import Plan, Subscription
from app.models.professional import Professional
from app.services.plan_catalog_seed import COMMERCIAL_PLAN_SEEDS
from app.services.saas_billing_service import SaasBillingService


@pytest.mark.asyncio
async def test_stub_webhook_activates_subscription(db_session):
    plan = Plan(**COMMERCIAL_PLAN_SEEDS[0])
    professional = Professional(
        email="billing@test.com",
        password_hash="hash",
        name="Billing User",
        subscription_status="trialing",
        trial_started_at=datetime.now(UTC),
        trial_ends_at=datetime.now(UTC),
    )
    db_session.add_all([plan, professional])
    await db_session.flush()

    sub = Subscription(
        professional_id=professional.id,
        plan_id=plan.id,
        status="incomplete",
        provider="stub",
        external_subscription_id="stub_sub_test",
        external_checkout_id="stub_pay_test",
    )
    db_session.add(sub)
    await db_session.commit()

    professional_id = str(professional.id)
    normalizer = StubWebhookNormalizer()
    events = normalizer.normalize(
        {
            "id": "evt-1",
            "event_type": InternalBillingEventType.PAYMENT_SUCCEEDED.value,
            "professional_id": professional_id,
            "plan_slug": plan.slug,
            "provider": "stub",
            "external_subscription_id": "stub_sub_test",
            "subscription_status": "active",
        },
        {},
    )

    billing = SaasBillingService(db_session)
    row = await billing.record_webhook_raw(
        provider="stub",
        external_event_id=events[0].external_event_id,
        event_type=events[0].event_type.value,
        payload=events[0].payload,
        professional_id=professional_id,
    )
    assert row is not None
    await billing.apply_normalized_events(events)

    await db_session.refresh(professional)
    await db_session.refresh(sub)
    assert professional.subscription_status == "active"
    assert sub.status == "active"
