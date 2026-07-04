"""Reconciliation must not auto-activate stub subscriptions."""

from datetime import UTC, datetime

import pytest

from app.models.billing import Plan, Subscription
from app.models.professional import Professional
from app.services.billing_reconciliation_service import BillingReconciliationService
from app.services.plan_catalog_seed import COMMERCIAL_PLAN_SEEDS


@pytest.mark.asyncio
async def test_reconcile_stub_does_not_activate_without_payment(db_session):
    plan = Plan(**COMMERCIAL_PLAN_SEEDS[0])
    professional = Professional(
        email="stub-reconcile@test.com",
        password_hash="hash",
        name="Stub User",
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
        external_subscription_id="stub_sub_x",
        external_checkout_id="stub_pay_x",
    )
    db_session.add(sub)
    await db_session.commit()

    service = BillingReconciliationService(db_session)
    result = await service.reconcile_professional(professional.id)

    assert result["applied"] is False
    await db_session.refresh(professional)
    await db_session.refresh(sub)
    assert professional.subscription_status == "trialing"
    assert sub.status == "incomplete"


@pytest.mark.asyncio
async def test_simulate_stub_payment_activates_explicitly(db_session):
    plan = Plan(**COMMERCIAL_PLAN_SEEDS[0])
    professional = Professional(
        email="stub-simulate@test.com",
        password_hash="hash",
        name="Stub Simulate",
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
        external_subscription_id="stub_sub_y",
        external_checkout_id="stub_pay_y",
    )
    db_session.add(sub)
    await db_session.commit()

    service = BillingReconciliationService(db_session)
    result = await service.simulate_stub_payment(professional.id)

    assert result["applied"] is True
    await db_session.refresh(professional)
    await db_session.refresh(sub)
    assert professional.subscription_status == "active"
    assert sub.status == "active"
